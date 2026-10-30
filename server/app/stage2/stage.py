"""Options (2A), master (2B) and first-cut stage logic. Session JSON in storage ({run}/stage2/session.json); films and plans are files;
stage outputs are the record. Validator decides; the chat model proposes; the operator decides per option in chat."""
import hashlib
import json
import re
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from psycopg.types.json import Jsonb

from .. import core, jobs
from ..errors import Problem
from . import CONTRACT_MASTER, CONTRACT_OPTIONS, SLATE_FRAMES, narration as NR, package as P, slides as SL, validator as V

TIMELINE = {'width': 1920, 'height': 1080, 'fps': 25}
BOUNDARY_PROMPT = ('Targeted boundary check (blueprint v3.2 §3 step 1.4). Watch ONLY the interval given below, which surrounds a planned cut point of a clip where a speaker was trimmed out. '
                   'Answer whether any residual lip movement or a look at the lens is visible inside the interval, with the exact seconds of the last such movement if any. Do not describe anything else.')
BOUNDARY_SCHEMA = {'type': 'object', 'properties': {'residual_lip_movement': {'type': 'string', 'enum': ['yes', 'no', 'unclear']}, 'last_movement_s': {'anyOf': [{'type': 'number'}, {'type': 'null'}]},
                                                    'looking_at_lens': {'type': 'string', 'enum': ['yes', 'no', 'unclear']}, 'notes': {'type': 'string'}},
                   'required': ['residual_lip_movement', 'last_movement_s', 'looking_at_lens', 'notes'], 'additionalProperties': False}


def fail(message, code='STAGE2_CONTRACT'):
    raise Problem(422, code, str(message))


def key(run, name):
    return f"{run['id']}/stage2/{name}"


def load_json(store, k):
    return json.loads(store.get(k).decode('utf-8'))


def save_json(store, k, value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')
    store.put(k, data, 'application/json')
    return {'key': k, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str).encode()).hexdigest()


def session_of(store, run, create=False):
    try:
        return load_json(store, key(run, 'session.json'))
    except Problem:
        if store.exists(key(run, 'session.json')):
            raise   # a failed read is not a missing session: starting a new one would drop recorded work
        if not create:
            raise Problem(409, 'NOT_ALLOWED', 'Run `vw options prepare` first.')
    return {'contract': 'vw2-stage2-session-v1', 'package': None, 'versions': [], 'current': None, 'accepted': None, 'frames': {}, 'inspections': {},
            'renders': {}, 'decisions': {}, 'extra_rules': [], 'master': None, 'recorded': {}}


def save_session(store, run, session):
    session['updated_at'] = datetime.now(timezone.utc).isoformat()
    save_json(store, key(run, 'session.json'), session)
    return session


def _output(outputs, stage, unit=None):
    o = next((o for o in outputs if o['stage'] == stage and o['unit'] == unit), None)
    if not o:
        raise Problem(409, 'NOT_ALLOWED', f'This step needs an accepted {stage} first.')
    return o


def _file(store, output, name):
    ref = next((f for f in output['files'] if f['name'] == name or f['name'].endswith('/' + name) or f['name'].endswith(name)), None)
    if not ref:
        raise Problem(409, 'FILE_MISSING', f"{name} is not recorded on the {output['stage']} output.")
    return load_json(store, ref['key']), ref


def _bump(conn, run, stage, errors):
    st = core._stage(core.stage_table(run['procedure_version']), stage)
    core._bump_attempt(run['id'], stage, None, st['cap'])
    row = conn.execute("select count, blocked from vw2_attempts where run_id=%s and stage=%s and unit=%s", (run['id'], stage, core.UNIT_NONE)).fetchone()
    count = (row or {}).get('count') or 1
    if row and row['blocked'] and count > st['cap']:
        raise Problem(409, 'NEEDS_USER_DECISION', f"The {stage} proposal was refused {count} times: {errors[0]}", options=['retry', 'revise', 'defect', 'stop'])
    raise Problem(422, f'{stage.upper()}_REJECTED', '; '.join(errors[:6]), attempt=count, cap=st['cap'], refusals=errors)


def _check_blocked(conn, run, stage):
    row = conn.execute("select count, blocked from vw2_attempts where run_id=%s and stage=%s and unit=%s", (run['id'], stage, core.UNIT_NONE)).fetchone()
    if row and row['blocked']:
        raise Problem(409, 'NEEDS_USER_DECISION', f"The {stage} proposal was refused {row['count']} times; ask the operator how to proceed.", options=['retry', 'revise', 'defect', 'stop'])


# ---------- options: prepare ----------

def learned_rules(conn, run):
    return core.client_rules(conn, run.get('client_id') or '')   # one source for every stage (design/37 2.7)


def prepare(conn, store, user, run, outputs):
    procedure = core._stage(core.stage_table(run['procedure_version']), 'options')
    brief_o, script_o, voice_o, media_o = (_output(outputs, s) for s in ('brief', 'script', 'voice', 'media'))
    brief, _ = _file(store, brief_o, 'brief.json')
    script, _ = _file(store, script_o, 'script.json')
    timing, _ = _file(store, voice_o, 'timing.json')
    production = brief_o['summary'].get('production') or {}
    beats = script.get('beats') or []
    if not beats:
        fail('The script has no beats; re-record the script on this build.')
    session = session_of(store, run, create=True)
    approved = session.get('scenes')
    words = timing['words']
    duration = voice_o['summary'].get('duration_s') or timing['audio']['duration_s']
    try:
        if approved:
            plan, to_tl = NR.plan(words, duration, TIMELINE['fps'], approved['document'].get('pauses') or [])
            windows = NR.beats(words, approved['document']['scenes'], plan, to_tl, TIMELINE['fps'])
        else:
            plan, to_tl = NR.plan(words, duration, TIMELINE['fps'])
            windows = NR.beats(words, NR.paragraph_scenes(beats, words), plan, to_tl, TIMELINE['fps'], ids=[b['beat_id'] for b in beats])
    except ValueError as exc:
        fail(exc)
    narration = {**plan, 'scenes_approved': bool(approved), 'words': NR.word_rows(words, TIMELINE['fps'], to_tl),
                 'sentences': NR.sentences(words, TIMELINE['fps'], to_tl), 'silences': NR.silences(words, TIMELINE['fps'], to_tl, plan['total_frames']),
                 'pause_rules': {'only_after_sentence_end': True, 'max_seconds': NR.MAX_PAUSE_S, 'seconds_means': 'total silence wanted; the recording\'s own gap counts toward it'}}
    clips = {c['id']: c for c in media_o['summary']['clips']}
    cards, rows, landmarks, entities, policy = [], [], set(), [], None
    for o in outputs:
        if o['stage'] != 'analysis' or o['unit'] is None or o['summary'].get('excluded'):
            continue
        if o['summary'].get('contract_version') != 'clip-log-v1':
            raise Problem(409, 'NOT_ALLOWED', 'Options need clip-log-v1 analysis (procedure version 2).')
        ref = next((f for f in o['files'] if f['name'].endswith('.evidence.json')), None)
        doc = load_json(store, ref['key'])
        log, clip = doc['log'], clips.get(o['unit'])
        if not clip:
            continue
        policy = policy or (doc['identity'].get('speaker_policy') or {})
        cards.append({'clip_id': clip['id'], 'clip_name': clip['name'], 'descriptive_name': log.get('descriptive_name'), 'lines': log.get('summary_card_lines') or []})
        for sub in log.get('sub_clips') or []:
            rows.append(P.sub_clip_row(clip, log, sub, TIMELINE['fps']))
            landmarks.update((sub.get('continuity_and_story') or {}).get('world_landmarks_and_props') or [])
        entities.extend({'clip_id': clip['id'], **e} for e in log.get('entities') or [])
    if not rows:
        raise Problem(409, 'NOT_ALLOWED', 'No analysed clips; run analysis first.')
    if approved:   # design/125 P8: the logs know the script's paragraphs; each is mapped to the approved scenes its words fall in, beside the chapter
        at = {w['id']: w for w in narration['words']}
        paragraphs = {}
        for b in beats:
            own = [w['id'] for w in words if w.get('passage_id') == b.get('passage_id')]
            if own:
                paragraphs[b['beat_id']] = (at[own[0]]['start_frame'], at[own[-1]]['end_frame'])
        P.scene_fits(rows, windows, paragraphs)
    rules = core.effective_rules(conn, run, outputs)['learned']   # design/37 2.7
    pk = P.build(run, production, windows, cards, rows, landmarks, entities, rules, TIMELINE, policy or {}, procedure.get('prompt') or '', narration)
    saved = save_json(store, key(run, 'package.json'), pk)
    session['package'] = {**saved, 'digest': digest({k: pk[k] for k in ('beats', 'sub_clips', 'timeline', 'policy', 'narration')}), 'beats': windows, 'timeline': TIMELINE, 'policy': policy or {},
                          'narration_key': next(f['key'] for f in voice_o['files'] if f['name'] == 'narration.mp3'), 'clips': {c['id']: c for c in media_o['summary']['clips']},
                          'narration': {k: plan[k] for k in ('pieces', 'total_frames', 'fps', 'cuts')}}
    save_session(store, run, session)
    eligible = sum(1 for r in rows if r['eligibility'].startswith('ELIGIBLE'))
    return {'package': saved, 'beats': len(windows), 'clips': len(cards), 'sub_clips': len(rows), 'eligible_sub_clips': eligible, 'coverage': pk['coverage'],
            'learned_rules': len(rules), 'scenes_approved': bool(approved), 'pauses': len(plan['cuts']), 'sentences': len(narration['sentences']),
            'next': prepare_next(bool(approved))}


def prepare_next(approved):
    """design/125 P1: the scenes come first, always."""
    return ('present the coverage report, then author out/options.json and `vw options check`' if approved else
            'propose the scenes and pauses first (out/scenes.json, `vw options scenes`); then the coverage report and the options')


def set_scenes(conn, store, user, run, outputs, document, quote):
    """design/19 A1–A3: scene boundaries (sentence starts) and sentence-end pauses on the existing narration, approved with one quote."""
    if not str(quote or '').strip():
        fail("The operator's approval of the scenes and pauses is required (--quote).")
    brief_o, script_o, voice_o = (_output(outputs, s) for s in ('brief', 'script', 'voice'))
    script, _ = _file(store, script_o, 'script.json')
    timing, _ = _file(store, voice_o, 'timing.json')
    words = timing['words']
    if ' '.join(w['text'] for w in words) != ' '.join(script['spoken_text'].split()):
        fail('The narration timing does not match the accepted script word for word; narrate again before splitting scenes.')
    stages = (brief_o['summary'].get('production') or {}).get('process_stages') or []
    duration = voice_o['summary'].get('duration_s') or timing['audio']['duration_s']
    try:
        document = {**document, 'scenes': NR.normalise_scenes(document.get('scenes'))}
        NR.validate_scenes(words, document.get('scenes'), stages)
        plan, to_tl = NR.plan(words, duration, TIMELINE['fps'], document.get('pauses') or [])
        bs = NR.beats(words, document['scenes'], plan, to_tl, TIMELINE['fps'])
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        fail(exc)
    session = session_of(store, run, create=True)
    version = (session.get('scenes') or {}).get('version', 0) + 1
    record = {'version': version, 'document': {'scenes': document['scenes'], 'pauses': document.get('pauses') or []}, 'quote': quote, 'by': user['id'],
              'at': datetime.now(timezone.utc).isoformat()}
    saved = save_json(store, key(run, f'scenes-v{version}.json'), record)
    session['scenes'] = {**record, 'file': saved, 'digest': digest(record['document'])}
    session['current'] = None          # options built on the old beats no longer apply
    session['accepted'] = None
    session['renders'].pop('review', None)
    save_session(store, run, session)
    out = prepare(conn, store, user, run, outputs)
    return {**out, 'scenes': [{k: b[k] for k in ('beat_id', 'title', 'target_beat_frames', 'process_stages')} | {'seconds': round(b['target_beat_frames'] / TIMELINE['fps'], 2),
                                                                                                                  'pauses': [{'after_word_id': p['after_word_id'], 'inserted_s': round(p['inserted_frames'] / TIMELINE['fps'], 2)} for p in b['pauses']]}
                                for b in bs],
            'film_seconds': round(plan['total_frames'] / TIMELINE['fps'], 2), 'inserted_seconds': round(plan['inserted_frames'] / TIMELINE['fps'], 2),
            'warnings': NR.chapter_warnings(document['scenes'])}   # design/125 P7


def coverage(store, run):
    session = session_of(store, run)
    return {'coverage': load_json(store, session['package']['key'])['coverage'], 'beats': session['package']['beats']}


def _package(store, session):
    return load_json(store, session['package']['key'])


def check(store, run, doc):
    session = session_of(store, run)
    pk = _package(store, session)
    if doc.get('contract') != CONTRACT_OPTIONS:
        return {'status': 'rejected', 'refusals': [f"contract must be {CONTRACT_OPTIONS}"], 'flags': []}
    work = deepcopy(doc)
    result = V.validate_options(work, pk, session['package']['policy'])
    out = {'status': 'rejected' if result['refusals'] else 'valid', 'refusals': result['refusals'],
           **V.answer_flags(result['flags']), 'flags_total': len(result['flags'])}   # design/125 P11
    if not result['refusals']:
        out['scenes'] = SL.scene_summary(work, pk, TIMELINE['fps'])
    return out


def propose(conn, store, user, run, doc):
    session = session_of(store, run)
    if not session.get('scenes'):   # design/43 7.3: titles, chapters and pauses are approved before any option
        raise Problem(409, 'NOT_ALLOWED', 'Propose the scenes first (`vw options scenes --file out/scenes.json --quote "…"`).')
    _check_blocked(conn, run, 'options')
    pk = _package(store, session)
    if doc.get('contract') != CONTRACT_OPTIONS:
        _bump(conn, run, 'options', [f'contract must be {CONTRACT_OPTIONS}'])
    work = deepcopy(doc)
    result = V.validate_options(work, pk, session['package']['policy'])
    if result['refusals']:
        _bump(conn, run, 'options', result['refusals'])
    for o in work['options']:
        for ev in o['events']:
            ev['timeline_frames'] = ev.pop('_timeline_frames')
            ev['fps_ratio'] = ev.pop('_fps_ratio')
    slides = SL.slides(work, pk, TIMELINE['fps'])
    scenes = SL.scene_summary(work, pk, TIMELINE['fps'])
    version = len(session['versions']) + 1
    record = {'run_id': str(run['id']), 'version': version, 'package_digest': session['package']['digest'], 'document': work, 'flags': result['flags'], 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    saved = save_json(store, key(run, f'options-v{version}.json'), record)
    identity = digest(work)
    session['versions'].append({'version': version, 'file': saved, 'digest': identity, 'flags': result['flags'], 'options': len(work['options']), 'gaps': [g['beat_id'] for g in work.get('gaps') or []],
                                'slides': slides, 'scenes': scenes})
    session['current'] = identity
    session['accepted'] = None
    session['decisions'] = {}
    session['master'] = None
    session['renders'].pop('review', None)
    conn.execute("delete from vw2_attempts where run_id=%s and stage='options' and unit=%s", (run['id'], core.UNIT_NONE))
    save_session(store, run, session)
    return {'version': version, 'digest': identity, 'options': len(work['options']), 'gaps': session['versions'][-1]['gaps'],
            **V.answer_flags(result['flags']), 'flags_total': len(result['flags']), 'scenes': scenes,
            'slides': [{k: s.get(k) for k in ('no', 'type', 'title', 'b_roll', 'note', 'of') if s.get(k) is not None} | {'seconds': round(s['frames'] / TIMELINE['fps'], 2)} for s in slides],
            **({'advice': round_advice(version)} if round_advice(version) else {}),
            'next': PROPOSE_NEXT}


PROPOSE_NEXT = '`vw options render`; the operator watches and answers the slides on the page; the first answer approves the options'   # design/125 P14
ROUNDS_BEFORE_BLANKS = 3


def round_advice(version):
    """Agreed with SK on 16 Oct: after three review rounds the assistant suggests leaving the scenes that keep failing blank."""
    if version > ROUNDS_BEFORE_BLANKS:
        return (f'This is review round {version}. Before proposing more footage, suggest to the operator that the scenes still not approved '
                'become blanks for AI video or animation, and ask which scenes to keep trying.')
    return None


def _slides(store, session, doc, entry):
    """The version's stored rows. A version proposed before design/21 carries none, one before design/127 is in the old form: both refused."""
    if 'slides' not in entry:
        raise Problem(409, 'NOT_ALLOWED', f"Version {entry['version']} has no stored slides (proposed before design/21): `vw options check` and `propose` again.")
    if any(s.get('scheme') != 3 for s in entry['slides']):   # design/127: scenes and shots; a cut in the old form (letters, second choices) is proposed again
        raise Problem(409, 'NOT_ALLOWED', f"Version {entry['version']} was proposed in the old form: the assistant proposes it again (`vw options propose`).")
    return entry['slides']


def current(store, session):
    if not session.get('current'):
        raise Problem(409, 'NOT_ALLOWED', 'Propose options first.')
    entry = next(v for v in session['versions'] if v['digest'] == session['current'])
    return load_json(store, entry['file']['key'])['document'], entry


def _same_package(store, session, entry):
    """design/43 7.8: a version answers the package it was checked against; after a re-prepare that changed it, propose again."""
    stored = load_json(store, entry['file']['key']).get('package_digest')
    if stored and stored != session['package']['digest']:
        raise Problem(409, 'NOT_ALLOWED', f"The package changed since version {entry['version']} (a clip was re-solved or excluded): `vw options check` and `propose` again.")


def show(store, run, option_number):
    session = session_of(store, run)
    doc, entry = current(store, session)
    o = next((o for o in doc['options'] if o['option_number'] == option_number), None)
    if not o:
        fail(f'No option #{option_number} in version {entry["version"]}.')
    return o


def log_key(store, run, outputs, unit):
    o = next((o for o in outputs if o['stage'] == 'analysis' and o['unit'] == unit), None)
    if not o:
        fail(f'No analysed clip {unit}.')
    ref = next((f for f in o['files'] if f['name'].endswith('.evidence.json')), None)
    return {'unit': unit, 'key': ref['key'], 'sha256': ref['sha256']}


# ---------- boundary checks ----------

def _row(store, session, sub_clip_id):
    pk = _package(store, session)
    row = next((r for r in pk['sub_clips'] if r['sub_clip_id'] == sub_clip_id), None)
    if not row:
        fail(f'Unknown sub-clip {sub_clip_id}.')
    return pk, row


def frames(store, user, run, sub_clip_id, edge):
    """Unpaid: stills at in_tc ± 1.0 s (every 0.25 s) for the operator to look at before any paid check (design/17 A5)."""
    session = session_of(store, run)
    pk, row = _row(store, session, sub_clip_id)
    clip = session['package']['clips'][row['clip_id']]
    fps = Fraction(row['source_fps'])
    at = float(Fraction(row['in_frame'] if edge == 'in' else row['out_frame']) / fps)
    duration = float(clip.get('duration_s') or 0)
    times = [round(at + d, 3) for d in (-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0) if 0 <= at + d < duration - 0.04]
    rows = []
    with tempfile.TemporaryDirectory(prefix='vw2-frames-') as folder:
        original = Path(folder) / 'original.mp4'
        original.write_bytes(store.get(f"{run['id']}/media/{clip['name']}"))
        for i, t in enumerate(times):
            out = Path(folder) / f'F{i + 1}.png'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{t:.6f}', '-i', str(original), '-frames:v', '1', str(out)], check=True, capture_output=True, timeout=120)
            png = out.read_bytes()
            k = key(run, f"frames/{sub_clip_id.replace(':', '-')}-{edge}/F{i + 1}.png")
            store.put(k, png, 'image/png')
            rows.append({'frame_id': f'F{i + 1}', 'at_s': t, 'key': k, 'sha256': hashlib.sha256(png).hexdigest()})
    session['frames'][f'{sub_clip_id}:{edge}'] = {'times': times, 'frames': rows}
    save_session(store, run, session)
    return {'sub_clip_id': sub_clip_id, 'edge': edge, 'frames': rows}


def inspect(conn, store, user, run, sub_clip_id, edge):
    """Paid: one Gemini inspection of in_tc ± 1.0 s on the original clip (blueprint §3 step 1.4). Informed, not gated."""
    session = session_of(store, run)
    pk, row = _row(store, session, sub_clip_id)
    clip = session['package']['clips'][row['clip_id']]
    fps = Fraction(row['source_fps'])
    at = float(Fraction(row['in_frame'] if edge == 'in' else row['out_frame']) / fps)
    qid = f"{sub_clip_id.replace(':', '-')}-{edge}"
    if qid in session['inspections'] and session['inspections'][qid].get('status') in ('queued', 'running', 'retained'):
        raise Problem(409, 'JOB_OPEN', 'This boundary was already inspected or is in progress.', job_id=session['inspections'][qid].get('job_id'))
    prompt = BOUNDARY_PROMPT + f"\nINTERVAL: {max(0.0, at - 1.0):.3f} s to {at + 1.0:.3f} s of the attached original. Planned cut at {at:.3f} s ({edge} point of {sub_clip_id})."
    snap = {'kind': 'inspection', 'question': {'id': qid, 'sub_clip_id': sub_clip_id, 'edge': edge, 'at_s': at}, 'question_id': qid, 'mode': 'video', 'prompt': prompt, 'schema': BOUNDARY_SCHEMA,
            'sources': {clip['id']: {'name': clip['name'], 'sha256': clip['sha256']}}, 'frames': [], 'understand_audio': True}
    rk = save_json(store, key(run, f'inspection/{qid}.request.json'), snap)
    job = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'options',%s,'gemini',%s, gen_random_uuid()) returning id",
                       (run['id'], qid, Jsonb({'kind': 'inspection', 'procedure_version': run['procedure_version'], 'question_id': qid, 'request_key': rk['key'], 'mode': 'video',
                                               'sources': snap['sources'], 'frames': [], 'prompt_key': rk['key']}))).fetchone()
    session['inspections'][qid] = {'job_id': str(job['id']), 'status': 'queued', 'at_s': at}
    save_session(store, run, session)
    return {'queued': qid, 'job_id': str(job['id']), 'paid': True}


def _refresh(conn, store, run, session):
    for qid, j in session['inspections'].items():
        row = conn.execute('select status, result, error, cost from vw2_jobs where id=%s', (j['job_id'],)).fetchone()
        if row:
            j.update(status=row['status'], error=row['error'], cost=row['cost'])
            if row['status'] == 'retained' and row['result'] and row['result'].get('answer_key'):
                j['answer'] = load_json(store, row['result']['answer_key']).get('answer')
    for kind, r in session['renders'].items():
        row = conn.execute('select status, result, error from vw2_jobs where id=%s', (r['job_id'],)).fetchone()
        if row:
            r.update(status=row['status'], error=row['error'], result=row['result'])


# ---------- renders ----------

def _event_items(session, pk, events, rows):
    items = []
    for ev in events:
        row = rows[ev['sub_clip_id']]
        clip = session['package']['clips'][row['clip_id']]
        crop = row['crop_rect'] if ev.get('crop') in ('solver', 'hands_only') else None
        items.append({'kind': 'event', 'sub_clip_id': ev['sub_clip_id'], 'clip': {'id': clip['id'], 'name': clip['name'], 'sha256': clip['sha256'], 'fps': row['source_fps'],
                                                                                   'rotation_deg': row.get('horizon_rotation_deg') or 0.0, 'hdr': str(clip.get('color_transfer') or '').lower() in ('arib-std-b67', 'smpte2084')},
                      'source_in_frame': ev['source_in_frame'], 'source_out_frame': ev['source_out_frame'], 'timeline_frames': ev['timeline_frames'], 'crop_rect': crop,
                      'hold_last_frame': bool(ev.get('hold_last_frame')), 'a2': ev.get('a2_intervals') or []})
    return items


def render(conn, store, user, run, kind):
    session = session_of(store, run)
    pk = _package(store, session)
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    beats = {b['beat_id']: b for b in pk['beats']}
    if kind == 'review':
        doc, entry = current(store, session)
        _same_package(store, session, entry)
        items = SL.review_items(doc, pk, _slides(store, session, doc, entry), lambda evs: _event_items(session, pk, evs, rows), TIMELINE['fps'])
        version, plan_digest = entry['version'], entry['digest']
    else:
        if not session.get('master'):
            raise Problem(409, 'NOT_ALLOWED', 'Build the master first (`vw master build`).')
        items = []
        for ev in session['master']['plan']['events']:
            if ev['kind'] == 'gap':
                items.append({'kind': 'event', 'sub_clip_id': None, 'gap': True, 'timeline_frames': ev['timeline_frames'], 'beat_id': ev.get('gap_id') or ev['beat_id']})
            else:
                items += _event_items(session, pk, [ev], rows)
        version, plan_digest = session['master']['version'], session['master']['digest']
    open_job = session['renders'].get(kind)
    if open_job and open_job.get('status') in ('queued', 'running') and open_job.get('digest') == plan_digest:
        raise Problem(409, 'JOB_OPEN', f'The {kind} film is already rendering.', job_id=open_job['job_id'])
    plan = {'kind': kind, 'items': items, 'timeline': TIMELINE, 'narration_key': session['package']['narration_key'], 'narration': session['package'].get('narration'), 'version': version, 'digest': plan_digest,
            'out_key': key(run, f'{kind}-v{version}-{plan_digest[:8]}.mp4')}
    rk = save_json(store, key(run, f'render-{kind}-v{version}.json'), plan)
    job = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,%s,%s,'render',%s, gen_random_uuid()) returning id",
                       (run['id'], 'options' if kind == 'review' else 'master', kind, Jsonb({'kind': 'render', 'film': kind, 'plan_key': rk['key'], 'out_key': plan['out_key']}))).fetchone()
    frames = sum((int(it.get('frames') or SLATE_FRAMES) if it['kind'] == 'slate' else int(it.get('frames') or it.get('timeline_frames') or 0))
                 for it in items if it['kind'] != 'narration')   # design/43 7.2: the tool's estimate needs the length
    session['renders'][kind] = {'job_id': str(job['id']), 'status': 'queued', 'digest': plan_digest, 'version': version, 'out_key': plan['out_key'], 'frames': frames}
    save_session(store, run, session)
    return {'job_id': str(job['id']), 'film': kind, 'version': version, 'frames': frames, 'paid': False,
            'next': 'wait with `vw options status --wait 900` (or `vw master status`), then fetch and let the operator watch'}


def status(conn, store, run):
    try:
        session = session_of(store, run)
    except Problem:
        return {'state': 'not_prepared', 'next': 'prepare'}
    _refresh(conn, store, run, session)
    save_session(store, run, session)
    last = conn.execute("select result->'record'->>'frames_per_s' as rate from vw2_jobs where provider='render' and status='ready' and result->'record'->>'frames_per_s' is not null "
                        "order by updated_at desc limit 1").fetchone()   # design/43 7.2: the speed of the last render on this server
    return {'state': 'prepared', 'versions': [{k: v[k] for k in ('version', 'options', 'gaps', 'flags')} for v in session['versions']], 'current': session.get('current'),
            'render_rate_fps': float(last['rate']) if last and last['rate'] else None,
            'accepted': session.get('accepted'), 'renders': session['renders'], 'inspections': session['inspections'], 'decisions': session['decisions'],
            'master': {k: session['master'][k] for k in ('version', 'digest', 'gaps', 'events')} if session.get('master') else None, 'recorded': session['recorded']}


def _ready_film(session, kind, plan_digest):
    r = session['renders'].get(kind)
    if not r or r.get('status') != 'ready' or r.get('digest') != plan_digest or not (r.get('result') or {}).get('key'):
        raise Problem(409, 'NOT_ALLOWED', f'The {kind} film for this version is not rendered yet (`vw {"options" if kind == "review" else "master"} render`, then poll status).')
    return r['result']


def record_options(conn, store, user, run, quote, approved_by=None):
    """The options output, recorded by the first slide answer (design/98 D2, D6): approved_by {'how': 'first_answer', 'slide': …}. The explicit
    approval beside it is retired (design/125 P14), refused."""
    if not approved_by:
        raise Problem(409, 'NOT_ALLOWED', 'The separate options approval is retired: answering the first slide approves the options.')
    session = session_of(store, run)
    doc, entry = current(store, session)
    _same_package(store, session, entry)
    _refresh(conn, store, run, session)
    film = _ready_film(session, 'review', entry['digest'])
    files = [{'name': f"options-v{entry['version']}.json", **{k: entry['file'][k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True},
             {'name': 'review.mp4', 'key': film['key'], 'sha256': film['sha256'], 'bytes': film['bytes'], 'location': 'storage', 'receipt': True},
             {'name': 'package.json', **{k: session['package'][k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True}]
    for f in files:
        jobs.record_file(conn, run['id'], 'options', f['key'], f['name'], f['sha256'], f['bytes'], 'application/json' if f['name'].endswith('.json') else 'video/mp4')
    inspection_cost = [j.get('cost') for j in session['inspections'].values() if j.get('cost')]
    out = core.output(conn, user, run, {'stage': 'options', 'files': files, 'accepted_quote': quote,
                                        'summary': {'version': entry['version'], 'options_digest': entry['digest'], 'options': entry['options'], 'gaps': entry['gaps'], 'flags': len(entry['flags']),
                                                    'scenes': ({'version': session['scenes']['version'], 'digest': session['scenes']['digest'], 'quote': session['scenes']['quote'],
                                                                'pauses': len(session['scenes']['document']['pauses'])} if session.get('scenes') else None),
                                                    'slides': len(entry.get('slides') or []), 'shots': sum(1 for s in entry.get('slides') or [] if s['type'] == 'shot'),
                                                    'ai_shots': sum(1 for s in entry.get('slides') or [] if s['type'] == 'ai'),
                                                    'alternatives': sum(1 for s in entry.get('slides') or [] if s['type'] == 'alternative'), 'scene_summary': entry.get('scenes'),
                                                    'review_film': {'sha256': film['sha256'], 'duration_s': film.get('duration_s')}, 'inspection_cost': inspection_cost,
                                                    **({'approved_by': approved_by} if approved_by else {})}})
    session['accepted'] = {'version': entry['version'], 'digest': entry['digest'], 'quote': quote, 'output': str(out['id']),
                           **({'approved_by': {**approved_by, 'at': datetime.now(timezone.utc).isoformat()}} if approved_by else {})}
    session['recorded']['options'] = str(out['id'])
    save_session(store, run, session)
    return {'output': str(out['id']), 'version': entry['version'],
            'next': 'the operator answers every shot on the review page (or `vw master decide --slide 1.2 --action KEEP|REJECT|TRIM`)'}


# ---------- master ----------

def slide_label(value):
    """design/127: a scene is 2, its shots 2.1, 2.2, an alternative of shot 2.2 is 2.2A1; '#2.2a1' is accepted."""
    return str(value).strip().lstrip('#').strip().upper()


ANSWERED = ('shot', 'alternative')   # design/127: the rows answered KEEP / REJECT (/ TRIM); the one AI shot of an all-AI scene too
RETIRED_ACTIONS = {'KEEP_WITH_EDIT': 'KEEP_WITH_EDIT is retired: use TRIM on the shot (--edit "in:±frames,out:±frames").',
                   'DROP': 'DROP is retired: answer the shot KEEP, REJECT or TRIM.'}


def _action(decisions, slide):
    d = decisions.get(str(slide['no'])) if slide else None
    return d.get('action') if d else None


def _answerable(s):
    return s['type'] in ANSWERED or (s['type'] == 'ai' and bool(s.get('ai_only')))


def _of(slide, sl):
    return next((x for x in sl if x['no'] == slide.get('of')), None)


def needs_answer(slide, sl, decisions):
    """design/127: a footage shot needs its answer; an AI shot inside a scene and a scene header never do; the one AI shot of an all-AI scene does;
    an alternative only once its shot is rejected. Returns (needs, why)."""
    if not _answerable(slide):
        return False, None
    if slide['type'] == 'alternative':
        shot, act = _of(slide, sl), _action(decisions, _of(slide, sl))
        if act is None:
            return False, f"answer {shot['title']} first"
        if act != 'REJECT':
            return False, f"Shot {shot['no'].split('.')[1]} is kept: its alternatives are off"
        other = next((x for x in sl if x['type'] == 'alternative' and x.get('of') == slide['of'] and x['no'] != slide['no'] and _action(decisions, x) == 'KEEP'), None)
        if other:
            return False, f"{other['title']} is kept: the other alternatives are off"
    return True, None




def missing_answers(sl, decisions):
    return [str(s['no']) for s in sl if needs_answer(s, sl, decisions)[0] and str(s['no']) not in decisions]


def _slide_rows(sl, decisions):
    """One row per scene, shot and alternative, with the answer so far (the page and the chat path show the same)."""
    rows = []
    for s in sl:
        lab = str(s['no'])
        d = decisions.get(lab)
        needs, why = needs_answer(s, sl, decisions)
        rows.append({'slide': lab, **{k: s.get(k) for k in ('type', 'title', 'scene', 'number', 'colour', 'hint', 'words', 'clip', 'b_roll', 'note', 'of', 'ai_only', 'intent')},
                     'lines': list(s.get('lines') or []), 'seconds': round(s['frames'] / TIMELINE['fps'], 2), 'answerable': _answerable(s), 'needs_answer': needs, 'why': why,
                     'answer': ({k: d.get(k) for k in ('action', 'note', 'edit', 'by', 'at')} if d else None)})
    return rows


def _progress(rows):
    return {'answered': sum(1 for r in rows if r['needs_answer'] and r['answer']), 'of': sum(1 for r in rows if r['needs_answer']),
            'waiting': [r['slide'] for r in rows if r['needs_answer'] and not r['answer']]}


def slides_view(store, run):
    """Every row of the current version with the answer so far, and the labels still waiting (design/44 8.1)."""
    session = session_of(store, run)
    doc, entry = current(store, session)
    rows = _slide_rows(_slides(store, session, doc, entry), session.get('decisions') or {})
    return {'version': entry['version'], 'slides': rows, **_progress(rows)}


def slide_cues(plan, fps):
    """design/127: when each row starts and ends in the review film, in seconds, from the saved render plan: every item names its row (`slide`);
    a scene runs to the end of its last piece. Narration items take no screen time; a slate without a frame count is the standard slate."""
    cues, at = {}, 0
    scene = None
    for it in plan.get('items') or []:
        kind = it.get('kind')
        if kind == 'narration':
            continue
        frames = int(it.get('frames') or SLATE_FRAMES) if kind == 'slate' else int(it.get('frames') or it.get('timeline_frames') or 0)
        lab = it.get('slide')
        if lab:
            if '.' not in lab:
                scene = lab
            start = cues.get(lab, [round(at / fps, 2)])[0]
            cues[lab] = [start, round((at + frames) / fps, 2)]
            if scene and lab != scene and lab.split('.')[0] == scene:
                cues[scene][1] = round((at + frames) / fps, 2)
        at += frames
    return cues


_CUES = {}   # (plan key, version digest) → the row cues: a rendered version's plan never changes


def _cues_for(store, run, entry):
    k = (key(run, f"render-review-v{entry['version']}.json"), entry['digest'])
    if k not in _CUES:
        try:
            plan = load_json(store, k[0])
            _CUES[k] = slide_cues(plan, TIMELINE['fps']) if plan.get('digest') == entry['digest'] else {}
        except Problem:
            return {}
    return _CUES[k]


def review_view(conn, store, run):
    """design/62: what the review page shows. The current version's rows with their answers and lines, the review film of that version
    when it is rendered (with every row's start and end), the render state otherwise, and whether the options are recorded.
    A read: one storage read for the session, no write; the render state is refreshed from the jobs table in memory."""
    try:
        session = session_of(store, run)
    except Problem:
        return {'state': 'not_prepared'}
    if not session.get('current'):
        return {'state': 'no_version'}
    entry = next(v for v in session['versions'] if v['digest'] == session['current'])
    try:
        sl = _slides(store, session, None, entry)
    except Problem as e:   # design/127: a cut proposed in the old form is proposed again
        return {'state': 'old_form', 'message': e.message}
    _refresh(conn, store, run, session)
    rows = _slide_rows(sl, session.get('decisions') or {})
    r = session['renders'].get('review') or {}
    film, cues = None, {}
    is_current = bool(r) and r.get('digest') == entry['digest']
    if is_current and r.get('status') == 'ready' and (r.get('result') or {}).get('key'):
        film = {'key': r['result']['key'], 'duration_s': r['result'].get('duration_s'), 'sha256': r['result'].get('sha256')}
        cues = _cues_for(store, run, entry)
    accepted = session.get('accepted') or {}
    return {'state': 'prepared', 'version': entry['version'], 'digest': entry['digest'], 'slides': rows, **_progress(rows), 'film': film, 'cues': cues,
            'render': ({'status': r.get('status'), 'error': r.get('error'), 'current': is_current} if r else None),
            'accepted': bool(accepted) and accepted.get('digest') == entry['digest'], 'approved_by': accepted.get('approved_by'), 'master_built': bool(session.get('master'))}


def _refuse_answer(s, sl, decisions, lab, action, edit):
    """design/127: the answer each row takes, refused by name otherwise."""
    if action in RETIRED_ACTIONS:
        fail(RETIRED_ACTIONS[action])
    if action not in ('KEEP', 'REJECT', 'TRIM'):
        fail('action must be KEEP, REJECT or TRIM')
    if s['type'] == 'scene':
        shots = [x['no'] for x in sl if x['number'] == s['number'] and x['type'] == 'shot']
        fail(f"Scene {s['number']} is a header: decide its shots: {', '.join(shots)}." if shots else
             f"Scene {s['number']} is a header: answer its shot {s['number']}.1 (Keep AI: KEEP, Find footage: REJECT).")
    if s['type'] == 'ai' and not s.get('ai_only'):
        fail(f"{s['title']} is made with AI inside the scene: it needs no answer.")
    if s['type'] == 'ai' and action == 'TRIM':
        fail(f"{s['title']} is made with AI: Keep AI (KEEP) or Find footage (REJECT).")
    if action == 'TRIM' and s['type'] != 'shot':
        fail(f"TRIM is for a footage shot; {s['title']} takes KEEP or REJECT.")
    if action == 'TRIM' and not edit:
        fail('TRIM needs --edit "in:±frames,out:±frames" (source frames; a frame is 1/25 s on the timeline).')
    if s['type'] == 'alternative':
        needs, why = needs_answer(s, sl, decisions)
        if not needs:
            fail(why + ': its alternatives open when it is rejected.' if why.startswith('answer') else why + '.')


def decide(conn, store, user, run, slide_no, action, note, edit):
    """design/127: the operator answers by row: a footage shot KEEP, REJECT or TRIM; the AI shot of an all-AI scene KEEP (Keep AI) or REJECT
    (Find footage); an alternative KEEP or REJECT once its shot is rejected. design/98: the first answer approves the options (the options output
    recorded in the same call, once the review film is rendered); a REJECT needs no reason."""
    session = session_of(store, run)
    doc, entry = current(store, session)
    sl = _slides(store, session, doc, entry)
    lab = slide_label(slide_no)
    action = str(action or '').strip().upper()
    s = next((x for x in sl if str(x['no']).upper() == lab), None)
    if not s:
        fail(f"No slide #{lab}: the labels are now " + ', '.join(f"{x['no']} ({x['title']})" for x in sl if _answerable(x)) + '.')
    _refuse_answer(s, sl, session['decisions'], lab, action, edit)
    approved_now = not session.get('accepted')
    if approved_now:   # design/98 D2: the first answer approves these options, with what was answered
        record_options(conn, store, user, run, f'Approved by answering the review slides: first answer #{lab} {action}' + (f' — {note.strip()}' if str(note or '').strip() else ''),
                       {'how': 'first_answer', 'slide': lab})
        session = session_of(store, run)
    session['decisions'][lab] = {'action': action, 'type': s['type'], **({'edit': edit} if action == 'TRIM' else {}),
                                 'note': note or '', 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    session['master'] = None
    save_session(store, run, session)
    progress = _progress(_slide_rows(sl, session['decisions']))
    return {'slide': lab, 'type': s['type'], 'action': action, 'decided': progress['answered'], 'of': progress['of'],
            **({'options_approved': True} if approved_now else {})}


def add_rule(store, user, run, text, quote=''):
    """design/43 7.5: the only way a client rule is made; the operator's confirmation travels with it."""
    session = session_of(store, run)
    if not str(text or '').strip():
        fail('A rule needs text.')
    if not str(quote or '').strip():
        fail("A client rule needs the operator's confirmation (--quote).")
    session['extra_rules'].append({'rule': text.strip(), 'quote': quote.strip(), 'by': user['id']})
    save_session(store, run, session)
    return {'rules': len(session['extra_rules'])}


def _parse_edit(edit):
    out = {'in': 0, 'out': 0}
    for part in str(edit).split(','):
        k, _, v = part.strip().partition(':')
        if k in out:
            out[k] = int(v)
    return out


def _trim(ev, edit, row, tl_fps, title):
    """design/127: TRIM on one footage shot: its in and out moved by source frames, inside its usable window, its action peak and its hold."""
    e = _parse_edit(edit)
    a, z = ev['source_in_frame'] + e['in'], ev['source_out_frame'] + e['out']
    if not (row['in_frame'] <= a < z <= row['out_frame']):
        fail(f"the trim leaves {title} outside its usable window {row['in_frame']}-{row['out_frame']}")
    peak = row.get('action_peak')
    if peak and not (a <= peak['in_frame'] and peak['out_frame'] <= z):
        fail(f"the trim drops the action peak {peak['in_frame']}-{peak['out_frame']} of {title}")
    if (z - a) / Fraction(row['source_fps']) < row['min_hold_s']:
        fail(f"the trim makes {title} shorter than its hold {row['min_hold_s']} s")
    ev['source_in_frame'], ev['source_out_frame'] = a, z
    ev['timeline_frames'] = int(round((z - a) * Fraction(str(tl_fps)) / Fraction(row['source_fps'])))
    ev['edited'] = edit
    return ev


def build_master(conn, store, user, run):
    """design/127: per shot: KEEP the shot, TRIM it, or REJECT it for its kept alternative, else an AI stretch with its words; adjacent AI
    stretches merge; an all-AI scene answered Find footage goes back to the assistant."""
    session = session_of(store, run)
    if not session.get('accepted'):
        raise Problem(409, 'NOT_ALLOWED', 'Record the options stage first.')
    doc, entry = current(store, session)
    pk = _package(store, session)
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    beats = pk['beats']
    decisions = session['decisions']
    sl = _slides(store, session, doc, entry)
    missing = [f'#{lab}' for lab in missing_answers(sl, decisions)]
    if missing:
        fail(f"Every shot needs an answer; missing: {', '.join(missing)}")
    row_of = {(s['option_number'], s['type'], s.get('event_index'), s.get('alt_index')): s for s in sl}
    fps = TIMELINE['fps']
    kept = {}
    for o in deepcopy(doc['options']):
        n_scene = row_of[(o['option_number'], 'scene', None, None)]['number']
        events = []
        for i, ev in enumerate(o['events']):
            if ev.get('blank'):
                s = row_of[(o['option_number'], 'ai', i, None)]
                if s.get('ai_only') and _action(decisions, s) == 'REJECT':
                    fail(f"Scene {n_scene}: the operator asked to find footage (Find footage on {s['no']}): propose the scene again with footage "
                         "(`vw options propose`), or the operator answers Keep AI.")
                events.append(ev)
                continue
            s = row_of[(o['option_number'], 'shot', i, None)]
            act = _action(decisions, s)
            if act == 'TRIM':
                ev = _trim(ev, decisions[s['no']]['edit'], rows[ev['sub_clip_id']], fps, s['title'])
            if act == 'REJECT':
                alt = next((row_of[(o['option_number'], 'alternative', i, m)] for m in range(len(ev.get('alternatives') or []))
                            if _action(decisions, row_of[(o['option_number'], 'alternative', i, m)]) == 'KEEP'), None)
                if alt:
                    ev = {**ev['alternatives'][alt['alt_index']], 'timeline_frames': ev['timeline_frames'], 'from_alternative': alt['no']}
                else:
                    ev = {'blank': True, 'timeline_frames': ev['timeline_frames'], 'intent': f"in place of rejected {s['title']}: {s.get('words') or ''}".strip(),
                          'rejected': s['no'], 'title': s['title']}
            elif (ev.get('note') or {}).get('kind') == 'reuse':
                ev['reuse_approved'] = True
            events.append(ev)
        total = sum(ev['timeline_frames'] for ev in events)
        target = next(b['target_beat_frames'] for b in beats if b['beat_id'] == o['beat_id'])
        if total != target:
            fail(f"Scene {n_scene} after the trim is {total} frames; it needs {target}. Trim one shot and extend another in the same scene.")
        merged = []
        for ev in events:
            if ev.get('blank') and merged and merged[-1].get('blank'):
                merged[-1] = {**merged[-1], 'timeline_frames': merged[-1]['timeline_frames'] + ev['timeline_frames'], 'intent': f"{merged[-1]['intent']}; {ev['intent']}",
                              'rejected': merged[-1].get('rejected') or ev.get('rejected'), 'title': merged[-1].get('title') or ev.get('title')}
            else:
                merged.append(ev)
        for ev in merged:
            if ev.get('blank') and ev.get('rejected') and ev['timeline_frames'] < V.MIN_BLANK_S * fps:
                fail(f"Rejecting {ev['title']} leaves {ev['timeline_frames'] / fps:.1f} s of AI between two shots: keep it, trim a neighbour, or reject a neighbour too.")
        o['events'] = merged
        kept[o['beat_id']] = o
    words = (pk.get('narration') or {}).get('words') or []

    def spoken(a, z):
        return ' '.join(w['text'] for w in words if a <= w['start_frame'] < z)

    events, gaps, cursor = [], [], 0
    for b in beats:
        o = kept.get(b['beat_id'])
        passages = [p for p in [b.get('passage_id')] if p]
        if not o:
            n = b['target_beat_frames']
            events.append({'kind': 'gap', 'beat_id': b['beat_id'], 'gap_id': b['beat_id'], 'timeline_in_frame': cursor, 'timeline_out_frame': cursor + n, 'timeline_frames': n})
            gaps.append({'shot_id': b['beat_id'], 'start_frame': cursor, 'end_frame': cursor + n, 'passage_ids': passages, 'reason': f"no option | narration: {spoken(cursor, cursor + n)}"})
            cursor += n
            continue
        k = 0
        for ev in o['events']:
            n = ev['timeline_frames']
            if ev.get('blank'):   # design/21: a stretch of AI inside a scene is its own gap for the visuals stage
                k += 1
                gid = f"{b['beat_id']}-B{k}"
                events.append({'kind': 'gap', 'beat_id': b['beat_id'], 'gap_id': gid, 'timeline_in_frame': cursor, 'timeline_out_frame': cursor + n, 'timeline_frames': n})
                gaps.append({'shot_id': gid, 'start_frame': cursor, 'end_frame': cursor + n, 'passage_ids': passages, 'reason': f"{ev.get('intent', '')} | narration: {spoken(cursor, cursor + n)}"})
                cursor += n
                continue
            events.append({'kind': 'event', 'beat_id': b['beat_id'], 'approved_from_option': o['option_number'], **{k2: ev[k2] for k2 in ('sub_clip_id', 'source_in_frame', 'source_out_frame', 'timeline_frames')},
                           'crop': ev.get('crop', 'full'), 'hold_last_frame': bool(ev.get('hold_last_frame')), 'a2_intervals': ev.get('a2_intervals') or [], 'marker': ev.get('marker'),
                           'timeline_in_frame': cursor, 'timeline_out_frame': cursor + n, 'edited': ev.get('edited'), 'reuse_approved': bool(ev.get('reuse_approved')),
                           **({'from_alternative': ev['from_alternative']} if ev.get('from_alternative') else {})})
            cursor += n
    plan = {'contract': CONTRACT_MASTER, 'run_id': str(run['id']), 'options_version': entry['version'], 'options_digest': entry['digest'], 'timeline': TIMELINE, 'events': events,
            'gaps': gaps, 'duration_frames': cursor, 'decisions': decisions, 'extra_rules': session['extra_rules'],
            'sfx_cues': [{'sub_clip_id': r['sub_clip_id'], **c} for r in pk['sub_clips'] if any(e.get('sub_clip_id') == r['sub_clip_id'] for e in events) for c in r['sfx_cues']],
            'finishing_preview': _finishing(pk, events)}
    result = V.validate_master(plan, pk)
    if result['refusals']:
        fail('; '.join(result['refusals']))
    version = (session['master'] or {}).get('version', 0) + 1 if session.get('master') else 1
    saved = save_json(store, key(run, f'master-v{version}.json'), plan)
    session['master'] = {'version': version, 'digest': digest(plan), 'file': saved, 'plan': plan, 'gaps': [g['shot_id'] for g in gaps], 'events': len([e for e in events if e['kind'] == 'event']), 'flags': result['flags']}
    session['renders'].pop('master', None)
    save_session(store, run, session)
    return {'version': version, 'events': session['master']['events'], 'gaps': session['master']['gaps'], 'flags': result['flags'], 'duration_frames': cursor,
            'next': '`vw master render`, fetch, let the operator watch, then `vw master record --quote`'}


def _finishing(pk, events):
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    items = []
    for ev in events:
        if ev['kind'] != 'event':
            continue
        r = rows[ev['sub_clip_id']]
        if r.get('stabilization_needed'):
            items.append({'sub_clip_id': r['sub_clip_id'], 'item': 'Stabilization (Inspector > Video > Stabilization) or FFmpeg at assembly', 'timeline_in_frame': ev['timeline_in_frame']})
        if r.get('horizon_rotation_deg'):
            items.append({'sub_clip_id': r['sub_clip_id'], 'item': f"Horizon rotation {r['horizon_rotation_deg']}°", 'timeline_in_frame': ev['timeline_in_frame']})
        if ev.get('crop') == 'hands_only':
            items.append({'sub_clip_id': r['sub_clip_id'], 'item': 'Smart Reframe / Magic Mask / clean plate: hands-only crop', 'timeline_in_frame': ev['timeline_in_frame']})
    return items


FIRST_CUT_WORDS = "The approval must say the operator watched the film and listened to it (both words), e.g. 'yes, watched and listened'."


def _first_cut_output(conn, user, run, master_id, film, summary, quote):
    """The approved master film as the first cut: hash-bound to the film, the master's gaps and timeline (design/17 A50)."""
    files = [{'name': 'first-cut.mp4', 'key': film['key'], 'sha256': film['sha256'], 'bytes': film['bytes'], 'location': 'storage', 'receipt': True}]
    return core.output(conn, user, run, {'stage': 'first_cut', 'files': files, 'accepted_quote': quote,
                                         'summary': {'movie_sha256': film['sha256'], 'master_output': str(master_id), 'plan_digest': summary['plan_digest'], 'fps': summary['fps'],
                                                     'resolution': summary['resolution'], 'duration_frames': summary['duration_frames'], 'gaps': summary['gaps']}})


def record_master(conn, store, user, run, quote):
    """design/44 8.4: one approval records the master and the first cut; the quote must say watched and listened."""
    session = session_of(store, run)
    m = session.get('master')
    if not m:
        raise Problem(409, 'NOT_ALLOWED', 'Build the master first.')
    q = (quote or '').lower()
    if 'watch' not in q or 'listen' not in q:
        fail(FIRST_CUT_WORDS)
    _refresh(conn, store, run, session)
    film = _ready_film(session, 'master', m['digest'])
    files = [{'name': f"master-v{m['version']}.json", **{k: m['file'][k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True},
             {'name': 'master.mp4', 'key': film['key'], 'sha256': film['sha256'], 'bytes': film['bytes'], 'location': 'storage', 'receipt': True}]
    for f in files:
        jobs.record_file(conn, run['id'], 'master', f['key'], f['name'], f['sha256'], f['bytes'], 'application/json' if f['name'].endswith('.json') else 'video/mp4')
    # learned rules (design/43 7.5): only the rules the operator confirmed; rejection notes stay on this run's decisions
    plan = m['plan']
    added = 0
    for r in plan['extra_rules']:
        conn.execute("insert into vw2_client_rules(client_id, rule, source_run) values (%s,%s,%s)", (run.get('client_id') or '', r['rule'], run['code']))
        added += 1
    summary = {'version': m['version'], 'plan_digest': m['digest'], 'fps': str(TIMELINE['fps']), 'resolution': [TIMELINE['width'], TIMELINE['height']], 'duration_frames': plan['duration_frames'],
               'gaps': plan['gaps'], 'units': {'visuals': [g['shot_id'] for g in plan['gaps']]}, 'events': m['events'], 'learned_rules_added': added,
               'film': {'sha256': film['sha256'], 'duration_s': film.get('duration_s'), 'mix': (film.get('record') or {}).get('mix')}}
    out = core.output(conn, user, run, {'stage': 'master', 'files': files, 'accepted_quote': quote, 'summary': summary})
    first = _first_cut_output(conn, user, run, out['id'], files[1], summary, quote)
    session['recorded']['master'] = str(out['id'])
    session['recorded']['first_cut'] = str(first['id'])
    save_session(store, run, session)
    return {'output': str(out['id']), 'first_cut_output': str(first['id']), 'version': m['version'], 'gaps': [g['shot_id'] for g in summary['gaps']], 'learned_rules_added': added,
            'next': 'visuals for each gap' if summary['gaps'] else 'assembly'}


def record_first_cut(conn, store, user, run, outputs, quote):
    """Retired (design/44 8.4, design/125): the separate first-cut record is refused; `record_master` records both."""
    raise Problem(409, 'NOT_ALLOWED', 'The separate first-cut record is retired: the first cut is recorded with the master (`vw master record`).')
