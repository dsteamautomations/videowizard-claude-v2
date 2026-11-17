"""design/211, part A: finding the footage pictures. The digest of the clip analyses, trial frames, the look record, the search record.

Every name, signature and constant below is fixed by design/211 section 3. Nothing here is called for a round without `v == 2`
(`visuals_stage.round_v2`). Parts B and C read only the functions and constants named in design/211 section 4.

Where things are kept: the digest at `<run>/visuals/digest.json`; the trial frames and their looks in `<run>/visuals/trials.json` (with `fp`,
each thing's fingerprint when its frames were taken); the search record of a thing in `session['found']`; a kept frame as a `frame` reference
with `view`, `look`, `weak` and `trial`. `visuals_stage.add_reference` and `reject_reference` load and save the session themselves, so a
function here loads the session again after calling one.

A refusal is a named constant (a format string): raise it with `visuals_stage.need(False, NAME.format(...))`; a test asserts the message.
"""
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import ref_sets, runlog
from . import visuals_stage as V
from .errors import Problem

DIGEST_CONTRACT = 'vw2-refs-digest-v1'
TRIAL_SIDE, TRIAL_QUALITY = 640, 80   # a trial frame: a JPEG, long side at most, quality (page_flow.shrink)
TRIALS_PER_CALL = 8
TRIALS_PER_THING = 8
KEPT_PER_THING = 3
THINGS_PER_HELPER = 5
HELPERS = 6
LIMITS = {'trials_per_thing': TRIALS_PER_THING, 'kept_per_thing': KEPT_PER_THING, 'things_per_helper': THINGS_PER_HELPER, 'helpers': HELPERS}
SEEN_CHARS = 300   # a look's one line
VERDICTS = ('pass', 'weak', 'fail')
WHO = ('helper', 'assistant')
RESULTS = ('found', 'weak', 'none', 'not_searched')
FP_FIELDS = ('name', 'kind', 'identity', 'description', 'requirements', 'required_views', 'size')   # the plan fields a search and a set rest on

FRAME_RULE = ('A frame is a good reference when the thing is whole, not covered, large enough to read, sharp, and its shape and size can be read. '
              'Weak: one of these fails and the thing is still recognised. Fail: the thing is not in the frame or cannot be recognised.')

# ---------- "what next" (design/211 section 3.9): the answer carries one of these as `then`; the tool prints it and adds nothing ----------

FIND_START = ('The references come next. Run `vw visuals digest`. Then find each thing in the footage: start `vw-reference-finder` helpers, about 5 things each, '
              "up to 6 at a time, each given its group name, its thing ids, the run folder's path and the tool's command line (with 5 things or fewer, do it yourself). "
              'Each takes trial frames (`vw visuals trial`), looks at them and records what it saw (`vw visuals look`).')
FIND_WORDS = ('This run has no digest of its footage, so the search is by words only: `vw visuals elements` names the likely clips. Every frame still needs a look '
              '(`vw visuals trial`, then `vw visuals look`). Tell the operator the footage was searched by words only.')
TRIAL_NEXT = 'Read each trial frame, then record what you saw: `vw visuals look --file <file>`. A trial frame is not a reference.'
LOOK_MORE = '{n} thing(s) recorded. {left} are not searched yet: {ids}.'
LOOK_ALL = ('Every thing is searched. Write out/reference-round.json, one row per thing (element_id, rec, reason; `prompt` only for what the plan does not say; '
            '`first` on three things of different kinds), and send it: `vw visuals round --file out/reference-round.json`.')

# ---------- refusals ----------

TRIAL_TOO_MANY = 'A call takes at most {max} trial frames; {n} were asked. Nothing was cut.'
TRIAL_LIMIT = '{max} trial frames were already taken for {eid}: choose among them (`vw visuals look`).'
TRIAL_UNKNOWN_CLIP = '{clip} at {at_s} s: not a clip of this run, or the time is outside it.'
LOOK_UNKNOWN_TRIAL = 'No trial frame {trial} was taken for {eid}: a look is recorded only for a frame that was fetched (`vw visuals trial`).'
LOOK_VERDICT = '{eid}: the verdict of a look is pass, weak or fail, not {verdict!r}.'
LOOK_SEEN = '{eid}: a look says in one line what was seen, at most {max} characters.'
LOOK_VIEW = '{eid}: a kept frame names its view.'
KEEP_FAIL = '{eid}: frame {trial} has the verdict fail: it cannot be kept.'
KEEP_LIMIT = '{eid}: at most {max} frames are kept for a thing, one per view.'
KEEP_REJECTED = '{eid}: frame {trial} was rejected by the operator: it cannot be kept.'
LOOK_NOTHING = '{eid}: give its looks, or the clips searched, or why it was not searched (`not_searched`).'
FRAME_NO_LOOK = '{fid} of {eid} has no recorded look: look at it first (`vw visuals trial`, then `vw visuals look`).'
NOT_SEARCHED = '{eid} has no search record: search the footage for it (`vw visuals look`), or record why it was not searched.'
OLDER_ROUND = "This film's reference round was started before the footage search by looks: it runs to its end as it began. Nothing was recorded; follow `vw visuals status`."


def _now():
    return datetime.now(timezone.utc).isoformat()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _words(text):
    return ' '.join(str(text or '').split())


def _view_key(view):
    return _words(view).lower()   # two views that differ only in capitals or spaces are one


def _things(plan):
    """The elements a round takes: a graphic is drawn and an animal is carried by its words (visuals_stage.elements_answer)."""
    return [e for e in plan['elements'] if e['kind'] not in ('graphic', 'animal')]


def _element(plan, eid):
    element = next((e for e in _things(plan) if e['id'] == eid), None)
    V.need(element, f'Unknown element {eid}.')
    return element


def _plan_now(store, run, outputs):
    """The current plan, for a write of this part: refused on a film whose round is an older one (it behaves exactly as before)."""
    session = V.session_of(store, run, outputs)
    V.need(not session.get('round') or V.round_v2(session), OLDER_ROUND)
    return V.current_plan(store, session)


def _searched(session, element):
    """The thing's search record, when it was searched as the plan describes it now."""
    rec = ((session or {}).get('found') or {}).get(element['id'])
    return rec if rec and rec.get('fingerprint') == fingerprint(element) else None


def _has_footage(session):
    """`visuals_stage.prepare` writes `clip_safe_zoom`, one entry per analysed clip: empty means a film with no footage. A session without it
    is read as having footage, so a search is never skipped by mistake."""
    return (session or {}).get('clip_safe_zoom') != {}


def _analysed(outputs):
    """[(clip, evidence key)] of every analysed clip, the operator's exclusions left out: the outputs `visuals_stage.prepare` reads."""
    rows = []
    for o in outputs:
        if o['stage'] == 'analysis' and not (o.get('summary') or {}).get('excluded'):
            ref = next((f for f in o.get('files') or [] if f['name'].endswith('.evidence.json')), None)
            if ref:
                rows.append((str(o['unit']), ref['key']))
    return sorted(rows)


def all_searched(session, plan):
    """Nothing is left to search: the film has no footage, or every thing the round takes has its search record for the plan as it is now."""
    return not _has_footage(session) or all(_searched(session, e) for e in _things(plan))


def footage(store, run, outputs):
    """True when the run has at least one analysed clip (an `analysis` output, not excluded, contract clip-log-v1). A film with none
    skips the search: `round_frames` then asks for no search record."""
    return bool(_analysed(outputs))


# ---------- the digest ----------

def _part(s):
    window, cam = s.get('max_usable_window') or {}, s.get('camera_and_optics') or {}
    return {'id': s.get('sub_clip_id'), 'in_s': window.get('in_s'), 'out_s': window.get('out_s'), 'hero_s': s.get('hero_frame_s'), 'grade': s.get('usability_grade'),
            'role': s.get('shot_role'), 'size': cam.get('native_shot_size'), 'angle': cam.get('camera_angle'), 'action': s.get('visual_action_observed'),
            'uncertain': s.get('visual_action_uncertainty'), 'props': list((s.get('continuity_and_story') or {}).get('world_landmarks_and_props') or []),
            'people': (s.get('people_and_speaker_analysis') or {}).get('people_count'),
            'defects': [{k: d.get(k) for k in ('defect', 'in_tc', 'out_tc', 'description')} for d in (s.get('technical_qc_and_remediation') or {}).get('defects_detected') or []]}


def digest(store, run, outputs):
    """The digest of every analysed clip (design/211 section 3.1), built from the outputs `visuals_stage.prepare` reads and stored at
    `visuals_stage.key(run, 'digest.json')`; reused while its `stamp` is unchanged. Returns
    {'contract': DIGEST_CONTRACT, 'stamp', 'built_at', 'clips': [{'clip', 'name', 'duration_s', 'overview', 'light', 'entities': [...],
    'parts': [{'id', 'in_s', 'out_s', 'hero_s', 'grade', 'role', 'size', 'angle', 'action', 'uncertain', 'props', 'people', 'defects'}]}],
    'not_searched': [{'clip', 'name', 'reason'}]}."""
    rows, media, k = _analysed(outputs), V.media_clips(outputs), V.key(run, 'digest.json')
    stamp = _sha('\n'.join(f'{unit}:{ek}' for unit, ek in rows).encode('utf-8'))
    try:
        doc = V.load_json(store, k)
    except (Problem, ValueError):
        doc = {}
    built = doc.get('contract') == DIGEST_CONTRACT and doc.get('stamp') == stamp
    if not built:
        clips = []
        for unit, ek in rows:
            evidence = V.load_json(store, ek)
            if evidence.get('contract_version') != 'clip-log-v1':
                continue   # not read: it is named below as not searched
            log, clip = evidence['log'], media.get(unit) or {}
            clips.append({'clip': unit, 'name': clip.get('name') or unit, 'duration_s': clip.get('duration_s'), 'overview': log.get('clip_overview'), 'light': log.get('lighting_and_weather'),
                          'entities': [{f: e.get(f) for f in ('name', 'kind', 'first_seen_s', 'last_seen_s', 'description', 'uncertainty')} for e in log.get('entities') or []],
                          'parts': [_part(s) for s in log.get('sub_clips') or []]})
        doc = {'contract': DIGEST_CONTRACT, 'stamp': stamp, 'built_at': _now(), 'clips': clips}
    read = {c['clip'] for c in doc['clips']}
    left_out = {str(o['unit']) for o in outputs if o['stage'] == 'analysis' and (o.get('summary') or {}).get('excluded')}
    not_searched = [{'clip': cid, 'name': c.get('name') or cid, 'reason': 'no analysis'} for cid, c in media.items() if cid not in read and cid not in left_out]
    if not built or doc.get('not_searched') != not_searched:
        doc['not_searched'] = not_searched
        V.save_json(store, k, doc)
    return doc


def digest_answer(store, run, outputs):
    """What `GET /api/runs/{run_id}/visuals/digest` answers: {'digest', 'things': [ref_sets.thing_facts(...) + {'found': result or None}],
    'rule': FRAME_RULE, 'limits': LIMITS, 'then': FIND_START or FIND_WORDS}. The things are the elements the round takes (no graphic, no animal).
    A thing searched before the plan changed has `found` None: it is searched again. `then` is LOOK_ALL when nothing is left to search:
    a film with no footage, or a run taken over whose things all have their record."""
    session = V.session_of(store, run, outputs)
    plan = V.current_plan(store, session)
    media = V.media_clips(outputs)
    try:
        d = digest(store, run, outputs)
    except (Problem, KeyError, TypeError, ValueError):   # the digest cannot be built: the word match is the way back (design/211 section 5.3)
        d = {'contract': DIGEST_CONTRACT, 'stamp': '', 'built_at': None, 'clips': [],
             'not_searched': [{'clip': cid, 'name': c.get('name') or cid, 'reason': 'the digest could not be built'} for cid, c in media.items()]}
    things = [{**ref_sets.thing_facts(plan, session, e), 'found': (_searched(session, e) or {}).get('result')} for e in _things(plan)]
    left = [t for t in things if t['found'] is None]
    older = bool(session.get('round')) and not V.round_v2(session)   # design/211 review, N5: an older round runs to its end as it began; nothing here is for it
    return {'digest': d, 'things': things, 'rule': FRAME_RULE, 'limits': LIMITS,
            'then': OLDER_ROUND if older else LOOK_ALL if not media or not left else FIND_START if d['clips'] else FIND_WORDS}


# ---------- trial frames ----------

def _at(at_s):
    return round(float(at_s), 1)


def trial_id(clip, at_s):
    """The id of a trial frame: 't' + sha1('<clip>:<at_s rounded to 0.1>')[:12]. The same moment is the same frame, for any thing."""
    return 't' + hashlib.sha1(f'{clip}:{_at(at_s):.1f}'.encode('utf-8')).hexdigest()[:12]


def _trials(store, run):
    try:
        return V.load_json(store, V.key(run, 'trials.json'))
    except Problem:
        return {'trials': {}}


def _moment(media, row):
    """(clip, second rounded to 0.1, the refusal or None) of one asked frame."""
    row = row if isinstance(row, dict) else {}
    clip = row.get('clip')
    try:
        at = _at(row.get('at_s'))
    except (TypeError, ValueError):
        at = None
    c = media.get(clip) if isinstance(clip, str) else None
    ok = at is not None and c and 0 <= at < float(c.get('duration_s') or 0)
    return clip, at, None if ok else TRIAL_UNKNOWN_CLIP.format(clip=clip, at_s=at)


def cut_trials(store, run, outputs, frames):
    """Before the run's lock: the frames [{element_id, clip, at_s}] cut as small JPEGs, one download per clip. Returns a list, one entry per
    frame in order: {'clip', 'at_s', 'jpg': bytes} or {'clip', 'at_s', 'error': str}. Writes nothing. A moment whose frame is already stored
    has `jpg` None (it is not cut again); a call over the limit cuts nothing ([]): `trial_record` refuses it."""
    from .page_flow import shrink   # here, not at the top: page_flow imports the whole stage
    if not isinstance(frames, list) or len(frames) > TRIALS_PER_CALL:
        return []
    media, have = V.media_clips(outputs), _trials(store, run)['trials']
    out, wanted = [], {}
    for i, row in enumerate(frames):
        clip, at, refusal = _moment(media, row)
        out.append({'clip': clip, 'at_s': at, **({'error': refusal} if refusal else {'jpg': None})})
        if not refusal and trial_id(clip, at) not in have:
            wanted.setdefault(clip, {}).setdefault(at, []).append(i)
    for clip, moments in wanted.items():
        with tempfile.TemporaryDirectory(prefix='vw2-trial-') as folder:
            src = Path(folder) / 'src.mp4'
            try:
                src.write_bytes(store.get(f"{run['id']}/media/{media[clip]['name']}"))
            except (Problem, OSError):
                for i in [i for rows in moments.values() for i in rows]:
                    out[i] = {'clip': clip, 'at_s': out[i]['at_s'], 'error': 'The clip could not be read.'}
                continue
            for n, (at, rows) in enumerate(moments.items()):
                png = Path(folder) / f'{n}.png'
                try:   # the same command as a footage frame (visuals_stage.add_reference)
                    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{at:.6f}', '-i', str(src), '-frames:v', '1', str(png)], check=True, capture_output=True, timeout=120)
                    got = {'jpg': shrink(png.read_bytes(), TRIAL_SIDE, TRIAL_QUALITY)}
                except (subprocess.SubprocessError, OSError, ValueError):
                    got = {'error': 'The frame could not be cut at this moment.'}
                for i in rows:
                    out[i] = {'clip': clip, 'at_s': at, **got}
    return out


def _fresh(doc, element):
    """A thing whose plan fields changed since its trial frames were taken loses them, and its count starts again."""
    eid, fp, fps = element['id'], fingerprint(element), doc.setdefault('fp', {})
    if fps.get(eid) not in (None, fp):
        for tid, row in list(doc['trials'].items()):
            if eid in row['elements']:
                row['elements'].remove(eid)
                row['looks'].pop(eid, None)
                if not row['elements']:
                    del doc['trials'][tid]
    fps[eid] = fp


def trial_record(store, user, run, outputs, frames, cut):
    """Under the run's lock: the cut frames stored (`<run id>/visuals/trials/<trial id>.jpg`) and recorded in
    `visuals_stage.key(run, 'trials.json')`: {'trials': {id: {'id', 'clip', 'at_s', 'key', 'sha256', 'elements': [eid], 'looks': {eid: look},
    'at', 'by'}}}. Returns {'trials': [{'id', 'clip', 'at_s', 'key', 'elements'}], 'failed': [{'clip', 'at_s', 'reason'}], 'left': {eid: n},
    'then': TRIAL_NEXT}. Refuses TRIAL_TOO_MANY, TRIAL_LIMIT, TRIAL_UNKNOWN_CLIP. A trial frame is never a reference.
    TRIAL_TOO_MANY refuses the call; TRIAL_LIMIT and TRIAL_UNKNOWN_CLIP are the `reason` of that one moment in `failed`, and the others go on."""
    V.need(isinstance(frames, list) and frames, 'Give the trial frames: [{element_id, clip, at_s}].')
    V.need(len(frames) <= TRIALS_PER_CALL, TRIAL_TOO_MANY.format(max=TRIALS_PER_CALL, n=len(frames)))
    things = {e['id']: e for e in _things(_plan_now(store, run, outputs))}
    for row in frames:
        eid = row.get('element_id') if isinstance(row, dict) else row
        V.need(isinstance(eid, str) and eid in things, f'Unknown element {eid}.')
    media, doc = V.media_clips(outputs), _trials(store, run)
    asked = list(dict.fromkeys(row['element_id'] for row in frames))
    for eid in asked:
        _fresh(doc, things[eid])
    rows = doc['trials']
    count = lambda eid: sum(eid in t['elements'] for t in rows.values())
    made, failed = {}, []
    for i, row in enumerate(frames):
        eid = row['element_id']
        clip, at, refusal = _moment(media, row)
        tid = None if refusal else trial_id(clip, at)
        trial = rows.get(tid)
        if not refusal and not (trial and eid in trial['elements']) and count(eid) >= TRIALS_PER_THING:
            refusal = TRIAL_LIMIT.format(max=TRIALS_PER_THING, eid=eid)
        if not refusal and not trial:
            got = cut[i] if isinstance(cut, list) and i < len(cut) else {}
            if got.get('jpg'):
                k = V.key(run, f'trials/{tid}.jpg')
                store.put(k, got['jpg'], 'image/jpeg')
                trial = rows[tid] = {'id': tid, 'clip': clip, 'at_s': at, 'key': k, 'sha256': _sha(got['jpg']), 'elements': [], 'looks': {}, 'at': _now(), 'by': user['id']}
            else:
                refusal = got.get('error') or 'The frame was not cut: ask for it again.'
        if refusal:
            failed.append({'clip': clip, 'at_s': at, 'reason': refusal})
            continue
        if eid not in trial['elements']:
            trial['elements'].append(eid)
        made[tid] = trial
    V.save_json(store, V.key(run, 'trials.json'), doc)
    return {'trials': [{k: t[k] for k in ('id', 'clip', 'at_s', 'key', 'elements')} for t in made.values()], 'failed': failed,
            'left': {eid: TRIALS_PER_THING - count(eid) for eid in asked}, 'then': TRIAL_NEXT}


# ---------- the look record and the search record ----------

def _kept(session, eid):
    """The thing's looked footage frames that still stand (candidate or approved)."""
    return [r for r in ((session or {}).get('references') or {}).values()
            if r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved') and r.get('look')]


def _views(element):
    try:
        return list(ref_sets.view_names(element))
    except NotImplementedError:   # until part B is merged: the plan's own views
        return list(element.get('required_views') or [])


def _settle(session, element, **new):
    """The thing's search record after a change: `kept` is its standing looked frames in view order (the views of its set first, in their
    order; any other view after), and the result follows them. A round still at step 1 shows the same frames."""
    eid = element['id']
    rec = session.setdefault('found', {}).setdefault(eid, {'result': 'none', 'by': None, 'at': _now(), 'fingerprint': fingerprint(element), 'clips': [], 'note': '', 'kept': [], 'closest': None})
    rec.update(new)
    names = [_view_key(v) for v in _views(element)]
    kept = sorted(_kept(session, eid), key=lambda r: names.index(_view_key(r.get('view'))) if _view_key(r.get('view')) in names else len(names))
    rec['kept'] = [r['id'] for r in kept]
    if kept:
        rec.update(result='weak' if all(r.get('weak') for r in kept) else 'found', closest=None)
    elif rec['result'] in ('found', 'weak'):
        rec['result'] = 'none'
    rd = session.get('round') or {}
    if rd.get('v') == 2 and rd.get('pass') == 1 and eid in (rd.get('elements') or {}):
        rd['elements'][eid]['frames'] = list(rec['kept'])
    return rec


def _full(conn, store, user, run, outputs, element, trial):
    """The trial's moment as a full-size `frame` reference of the thing (visuals_stage.add_reference): the same trial gives the same reference."""
    eid = element['id']
    body = {'element_id': eid, 'name': f'frame-{eid}', 'kind': 'frame', 'subject': element.get('name') or eid, 'source_media_id': trial['clip'], 'requested_s': trial['at_s'],
            'request_id': f"look:{eid}:{trial['id']}"}
    try:
        return V.add_reference(conn, store, user, run, outputs, body, None)['id']
    except (subprocess.SubprocessError, OSError):
        raise ValueError(f"{eid}: frame {trial['id']} could not be cut at full size; send its look again.")


def _mark(session, trial, eid, ref_id, look):
    """One look, on its trial frame and on the kept frame."""
    trial['looks'][eid] = look
    session['references'][ref_id].update(view=look['view'], look=dict(look), weak=look['verdict'] == 'weak', trial=trial['id'])


def _not_rejected(session, eid, tid):
    V.need(not any(r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('trial') == tid and r.get('status') == 'rejected' for r in session['references'].values()),
           KEEP_REJECTED.format(eid=eid, trial=tid))


def look_extra(look, kind):
    """design/213: what a look may say beside its verdict, kept only as the looker gave it, true or false, never guessed from a word: `face`
    (the frame shows the person's face) and, for a person, `child` (the person is a child; the plan has no field for it)."""
    return {k: look[k] for k in (('face', 'child') if kind == 'person' else ('face',)) if isinstance(look.get(k), bool)}


def _look_one(conn, store, user, run, outputs, doc, element, thing, by):
    """One thing of `look_record`: everything is checked before anything is written. Returns its search record."""
    eid = element['id']
    _fresh(doc, element)
    thing = thing if isinstance(thing, dict) else {}
    looks, clips, why = thing.get('looks') or [], [str(c) for c in thing.get('clips') or []], _words(thing.get('not_searched'))
    V.need(isinstance(looks, list) and (looks or clips or why), LOOK_NOTHING.format(eid=eid))
    session = V.session_of(store, run, outputs)
    old = (session.get('found') or {}).get(eid)
    stale = [r['id'] for r in _kept(session, eid) if r['status'] == 'candidate'] if old and old.get('fingerprint') != fingerprint(element) else []
    rows = []
    for l in looks:
        l = l if isinstance(l, dict) else {}
        tid, verdict, seen, view = l.get('trial'), l.get('verdict'), _words(l.get('seen')), _words(l.get('view'))
        trial = doc['trials'].get(tid) if isinstance(tid, str) else None
        V.need(trial and eid in trial['elements'], LOOK_UNKNOWN_TRIAL.format(trial=tid, eid=eid))
        V.need(isinstance(verdict, str) and verdict in VERDICTS, LOOK_VERDICT.format(eid=eid, verdict=verdict))
        V.need(0 < len(seen) <= SEEN_CHARS, LOOK_SEEN.format(eid=eid, max=SEEN_CHARS))
        if l.get('keep'):
            V.need(view, LOOK_VIEW.format(eid=eid))
            V.need(verdict != 'fail', KEEP_FAIL.format(eid=eid, trial=tid))
            _not_rejected(session, eid, tid)
        rows.append({'trial': tid, 'view': view, 'verdict': verdict, 'seen': seen, 'keep': bool(l.get('keep')), 'closest': bool(l.get('closest')), 'extra': look_extra(l, element.get('kind'))})
    keeps = [r for r in rows if r['keep']]
    asked = {r['trial'] for r in keeps}
    unkept = {r['trial'] for r in rows if not r['keep']}   # design/211 review, N10: a look sent again without `keep` lets go of the frame kept for it, while the operator has not answered it
    stale += [r['id'] for r in _kept(session, eid) if r['status'] == 'candidate' and r.get('trial') in unkept and r['id'] not in stale]
    views = [_view_key(r['view']) for r in keeps] + [_view_key(r.get('view')) for r in _kept(session, eid) if r['id'] not in stale and r.get('trial') not in asked]
    V.need(len(views) <= KEPT_PER_THING and len(set(views)) == len(views), KEEP_LIMIT.format(eid=eid, max=KEPT_PER_THING))
    if stale:   # found as the plan described the thing before, and never answered by the operator: they go
        for rid in stale:
            del session['references'][rid]
        V.save_session(store, run, session)
    made = {tid: _full(conn, store, user, run, outputs, element, doc['trials'][tid]) for tid in asked}
    session, at, closest = V.session_of(store, run, outputs), _now(), None
    for r in rows:
        trial = doc['trials'][r['trial']]
        held = (trial['looks'].get(eid) or {}).get('ref')
        look = {'who': by, 'at': at, 'view': r['view'], 'verdict': r['verdict'], 'seen': r['seen'], 'trial': r['trial'], 'ref': made.get(r['trial']) or (held if held in session['references'] else None), **r['extra']}
        if r['keep']:
            _mark(session, trial, eid, look['ref'], look)
        else:
            trial['looks'][eid] = look
            closest = closest or (r['trial'] if r['closest'] else None)
    rec = _settle(session, element, result='not_searched' if why else 'none', by=by, at=at, fingerprint=fingerprint(element), clips=clips, note=why or _words(thing.get('note')), closest=closest)
    V.save_session(store, run, session)
    return rec


def look_record(conn, store, user, run, outputs, things, by):
    """The looks of `vw visuals look` (design/211 section 3.3): things = [{'element', 'clips', 'note', 'not_searched'?, 'looks': [{'trial',
    'view', 'verdict', 'seen', 'keep'?, 'closest'?, 'face'?, 'child'?}]}] (design/213: `face` and `child`, true or false, kept on the look). Each look is stored on its trial frame; a `keep` row becomes a `frame` reference
    through `visuals_stage.add_reference`, with `view`, `look`, `weak`, `trial` on it; the search record goes to `session['found'][eid]`
    with the result the server decides. Returns {'recorded': [eid], 'refused': {eid: message}, 'results': {eid: result},
    'kept': {eid: [reference ids]}, 'left': [eid], 'then': LOOK_MORE or LOOK_ALL}. A refused thing does not stop the others.
    A later record of a thing replaces the earlier one; its kept frames stay and count towards the limit."""
    V.need(isinstance(by, str) and by in WHO, '`by` says who looked: helper or assistant.')
    V.need(isinstance(things, list) and things, 'Give the things: [{element, clips, note, looks: [{trial, view, verdict, seen, keep}]}].')
    elements = {e['id']: e for e in _things(_plan_now(store, run, outputs))}
    doc = _trials(store, run)
    out = {'recorded': [], 'refused': {}, 'results': {}, 'kept': {}}
    for thing in things:
        eid = str(thing.get('element') if isinstance(thing, dict) else thing)
        try:
            V.need(eid in elements, f'Unknown element {eid}.')
            rec = _look_one(conn, store, user, run, outputs, doc, elements[eid], thing, by)
        except ValueError as exc:
            out['refused'][eid] = str(exc)
            continue
        out['recorded'].append(eid)
        out['results'][eid], out['kept'][eid] = rec['result'], list(rec['kept'])
    V.save_json(store, V.key(run, 'trials.json'), doc)
    session = V.session_of(store, run, outputs)
    left = [eid for eid, e in elements.items() if not _searched(session, e)]
    return {**out, 'left': left, 'then': LOOK_MORE.format(n=len(out['recorded']), left=len(left), ids=', '.join(left)) if left else LOOK_ALL}


def round_frames(session, plan, eid, named):
    """Called by `visuals_stage.round_start` for every row of a v2 round: the thing's frames that have a look, in view order (`named`: the
    ids the row gives, or empty for all). Refuses FRAME_NO_LOOK and, when the run has footage, NOT_SEARCHED. Returns [reference ids]."""
    V.need(not _has_footage(session) or eid in (session.get('found') or {}), NOT_SEARCHED.format(eid=eid))
    named = list(named or [])
    for fid in named:
        r = (session.get('references') or {}).get(fid)
        V.need(r and r.get('kind') == 'frame' and r.get('element_id') == eid and r.get('status') in ('candidate', 'approved'), f'{fid} is not a footage frame of {eid}.')
        V.need(r.get('look'), FRAME_NO_LOOK.format(fid=fid, eid=eid))
    return [f['ref'] for f in frames_of(session, eid) if not named or f['ref'] in named]


def frames_of(session, eid):
    """The thing's looked footage frames that are candidate or approved, in view order: [{'ref', 'view', 'verdict', 'seen', 'weak'}]."""
    order = (((session or {}).get('found') or {}).get(eid) or {}).get('kept') or []   # the view order, settled with the plan when the record was written
    rows = sorted(_kept(session, eid), key=lambda r: order.index(r['id']) if r['id'] in order else len(order))
    return [{'ref': r['id'], 'view': r.get('view'), 'verdict': r['look'].get('verdict'), 'seen': r['look'].get('seen'), 'weak': bool(r.get('weak'))} for r in rows]


def faces_of(session, eid):
    """design/213: the thing's kept footage frames whose look says they show the face, the best first: a look that passes before a weak
    one, then the view order. [reference ids]."""
    refs = (session or {}).get('references') or {}
    rows = [f for f in frames_of(session, eid) if ((refs.get(f['ref']) or {}).get('look') or {}).get('face') is True]
    return [f['ref'] for f in sorted(rows, key=lambda f: f['verdict'] != 'pass')]


def found_all(store, run, session, plan):
    """The search record of every thing, for the page and the chat: {eid: {'result', 'by', 'at', 'clips': count, 'clip_names': [first five],
    'not_searched': [clip names], 'note', 'closest': {'trial', 'key', 'sha256', 'view', 'seen'} or None, 'stale': bool}}. A thing with no record is absent."""
    try:
        d = V.load_json(store, V.key(run, 'digest.json'))
    except (Problem, ValueError):
        d = {}
    names = {c['clip']: c.get('name') or c['clip'] for c in [*(d.get('clips') or []), *(d.get('not_searched') or [])]}
    trials, out = _trials(store, run)['trials'], {}
    for e in plan['elements']:
        rec = ((session or {}).get('found') or {}).get(e['id'])
        if not rec:
            continue
        clips, trial = rec.get('clips') or [], trials.get(rec.get('closest'))
        look = ((trial or {}).get('looks') or {}).get(e['id']) or {}
        out[e['id']] = {'result': rec.get('result'), 'by': rec.get('by'), 'at': rec.get('at'), 'clips': len(clips), 'clip_names': [names.get(c, c) for c in clips[:5]],
                        'not_searched': [c.get('name') or c['clip'] for c in d.get('not_searched') or []], 'note': rec.get('note') or '',
                        'closest': {'trial': trial['id'], 'key': trial['key'], 'sha256': trial.get('sha256'), 'view': look.get('view'), 'seen': look.get('seen')} if trial else None,
                        'stale': rec.get('fingerprint') != fingerprint(e)}
    return out


def fingerprint(element):
    """sha256 of the plan fields a search and a set rest on: name, kind, identity, description, requirements, required_views, size."""
    return _sha(json.dumps({k: element.get(k) for k in FP_FIELDS}, sort_keys=True, ensure_ascii=False, default=str).encode('utf-8'))


# ---------- the operator's answers to a footage picture ----------

def _answered(conn, store, run, user, session, doc, element, entry, quote):
    """After the operator's answer: the record settled, both files saved, one line in the film's log with their words."""
    _settle(session, element)
    V.save_session(store, run, session)
    V.save_json(store, V.key(run, 'trials.json'), doc)
    if conn is not None:
        runlog.write(conn, {'run_id': run['id'], 'stage': 'visuals', 'kind': 'decision', 'about': f"thing {element['id']}", 'rule': 'design/211 (a footage picture, answered by the operator)',
                            'entry': entry, 'by_kind': 'operator', 'by_name': user.get('name') or '', 'quote': quote, 'request_id': None})


def not_this(conn, store, user, run, outputs, eid, ref_id, quote):
    """The operator's "Not this picture": the frame is rejected with their words; the best other looked trial frame of the same view (pass
    before weak, never fail) is kept in its place, without a new search. Returns {'next': reference id or None}."""
    session = V.session_of(store, run, outputs)
    element = _element(V.current_plan(store, session), eid)
    row = (session.get('references') or {}).get(ref_id)
    V.need(row and row.get('kind') == 'frame' and row.get('element_id') == eid, f'{ref_id} is not a footage frame of {eid}.')
    V.reject_reference(store, user, run, outputs, ref_id, quote, quote)   # with its own refusals: a picture a later step used is not changed
    session, doc = V.session_of(store, run, outputs), _trials(store, run)
    used = {r.get('trial') for r in session['references'].values() if r.get('kind') == 'frame' and r.get('element_id') == eid}
    others = [t for t in doc['trials'].values() if t['id'] not in used and (t['looks'].get(eid) or {}).get('verdict') in ('pass', 'weak')
              and _view_key(t['looks'][eid].get('view')) == _view_key(row.get('view'))]
    best = min(others, key=lambda t: t['looks'][eid]['verdict'] != 'pass', default=None)
    nxt = None
    if best:
        nxt = _full(conn, store, user, run, outputs, element, best)
        session = V.session_of(store, run, outputs)
        _mark(session, best, eid, nxt, {**best['looks'][eid], 'ref': nxt})
    _answered(conn, store, run, user, session, doc, element, f'not this picture ({ref_id})' + (f'; the next best of the same view is shown ({nxt})' if nxt else '; no other frame of that view was seen'),
              V.said(quote, 'Not this picture', user))
    return {'next': nxt}


def that_is_it(conn, store, user, run, outputs, eid, trial, quote):
    """The operator's "That is it" on the closest picture of a thing that was not found: the trial frame becomes a kept frame, weak.
    Returns {'ref': reference id}."""
    session = V.session_of(store, run, outputs)
    element = _element(V.current_plan(store, session), eid)
    doc = _trials(store, run)
    row = doc['trials'].get(trial) if isinstance(trial, str) else None
    V.need(row and eid in row['looks'], LOOK_UNKNOWN_TRIAL.format(trial=trial, eid=eid))
    _not_rejected(session, eid, trial)
    rid = _full(conn, store, user, run, outputs, element, row)
    session = V.session_of(store, run, outputs)
    _mark(session, row, eid, rid, {**row['looks'][eid], 'view': row['looks'][eid].get('view') or 'whole', 'verdict': 'weak', 'ref': rid})   # weak: kept on the operator's word, not on the look
    _answered(conn, store, run, user, session, doc, element, f'the closest picture is the thing ({rid})', V.said(quote, 'That is it', user))
    return {'ref': rid}
