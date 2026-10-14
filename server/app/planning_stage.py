"""Planning stage: the chat model is the sole planner; the server builds the package and checks the contract (v1 logic ported).

Session state is one small JSON object in storage ({run}/planning/session.json); plans, package, ledger and the handoff are
files. Flow: prepare → scenes → check/draft → answers (user / mechanical / frames / paid inspection) → review → ledger →
revise (any number of versions) → finalize (stage output + certificate) → handoff (compiled-edit-v2 for the Mac)."""
import base64
import hashlib
import json
import math
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from psycopg.types.json import Jsonb

from . import core, jobs, voice_timing
from .errors import Problem
from .planning import edit_clarification as clar
from .planning import planning_contract as contract
from .planning import planning_scene_groups as scenes_mod
from .planning import review_cards
from .planning.digest import digest
from .planning.planning_execution import execution_document
from .storage import storage
from .video_evidence.situation import validate_situation

STAGE = 'planning'
COMPONENTS = ('object_identity', 'person_hand_association', 'contact_state', 'movement_sequence', 'timestamp_mapping', 'question_scope')
FLAGS = ('user_constraints_respected', 'illustration_not_proof', 'certainty_overstatements_flagged', 'question_context_checked',
         'excerpt_claims_checked', 'reuse_checked', 'alternative_coverage_checked')


def fail(message):
    raise Problem(422, 'PLANNING_CONTRACT', str(message))


def guarded(fn):
    try:
        return fn()
    except (ValueError, KeyError, TypeError, ZeroDivisionError, OverflowError) as exc:
        fail(exc)


# ---------- session storage ----------

def key(run, name):
    return f"{run['id']}/planning/{name}"


def load_json(store, k):
    return json.loads(store.get(k).decode('utf-8'))


def save_json(store, k, value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')
    store.put(k, data, 'application/json')
    return {'key': k, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def session_of(store, run, required=True):
    try:
        return load_json(store, key(run, 'session.json'))
    except Problem:
        if required:
            raise Problem(409, 'NOT_ALLOWED', 'Run `vw planning prepare` first.')
        return None


def save_session(store, run, session):
    session['updated_at'] = datetime.now(timezone.utc).isoformat()
    save_json(store, key(run, 'session.json'), session)
    return session


# ---------- inputs from the v2 ledger ----------

def _output(outputs, stage):
    o = next((o for o in outputs if o['stage'] == stage and o['unit'] is None), None)
    if not o:
        raise Problem(409, 'NOT_ALLOWED', f'Planning needs an accepted {stage} first.')
    return o


def _file(store, output, name):
    ref = next((f for f in output['files'] if f['name'] == name), None)
    if not ref:
        raise Problem(409, 'FILE_MISSING', f'{name} is not recorded on the {output["stage"]} output.')
    return load_json(store, ref['key'])


def situation_from(settings):
    audio, visible = settings['source_audio_in_output'], settings['visible_speaking']
    situation = {'enabled': True, 'confirmed': True, 'situation_description': settings.get('film_type') or 'narrated documentary',
                 'source_audio_in_output': audio, 'talking_heads': 'to_be_assessed', 'visible_speaking': visible,
                 'story_carrier': 'supplied_narration', 'supplied_narration_policy': 'preserve',
                 'source_speech_under_b_roll': 'avoid', 'speaker_on_screen': 'allow' if visible == 'allow' else 'avoid',
                 'visible_speaking_exceptions': [], 'supplied_narration_instructions': '', 'speaker_selected_moments': []}
    try:
        return validate_situation(situation, require_resolved=True)
    except ValueError as exc:
        fail(exc)


def build_inputs(conn, store, run, outputs, settings):
    brief_o, script_o, voice_o, media_o = (_output(outputs, s) for s in ('brief', 'script', 'voice', 'media'))
    brief = _file(store, brief_o, 'brief.json') | {'content_digest': brief_o['summary'].get('content_digest')}
    script = _file(store, script_o, 'script.json')
    timing = _file(store, voice_o, 'timing.json')
    narration = next(f for f in voice_o['files'] if f['name'] == 'narration.mp3')
    media = _file(store, media_o, 'media.json')
    try:
        voice_timing.check_words(timing)
    except ValueError as exc:
        raise Problem(409, 'NARRATION_TIMING', str(exc))
    analyses = []
    excluded = []
    for o in outputs:
        if o['stage'] != 'analysis':
            continue
        if o['summary'].get('excluded'):
            excluded.append(o['unit'])
            continue
        ev_ref = next((f for f in o['files'] if f['name'].endswith('.evidence.json')), None)
        if not ev_ref:
            continue
        ev = load_json(store, ev_ref['key'])
        analyses.append({'id': o['summary'].get('job_id') or ev_ref['sha256'][:16], 'media_id': o['unit'], 'analysis_key': ev['identity'].get('schema_digest', '')[:16],
                         'evidence': ev['evidence'], 'evidence_binding': {'analysis_key': digest(ev['identity']), 'raw_digest': ev_ref['sha256'], 'result_digest': ev_ref['sha256'],
                                                                           'schema_digest': ev['identity'].get('schema_digest'), 'source_sha256': ev['clip']['sha256']}})
    analysed = {a['media_id'] for a in analyses}
    sources = []
    for c in media['clips']:
        if c['id'] in excluded or c['id'] not in analysed:
            continue
        fps = Fraction(str(c.get('fps') or '0/1'))
        if fps <= 0:
            fail(f"Clip {c['name']} has no frame rate.")
        sources.append({'id': c['id'], 'sha256': c['sha256'], 'size_bytes': c['bytes'], 'mime': 'video/mp4', 'original_name': c['name'], 'status': 'ready',
                        'metadata': {'average_fps': str(fps), 'duration_seconds': c['duration_s'], 'width': c['width'], 'height': c['height'],
                                     'frame_count': c.get('frame_count') or math.floor(Fraction(str(c['duration_s'])) * fps), 'audio_streams': [1] if c.get('has_audio') else []}})
    if not sources:
        raise Problem(409, 'NOT_ALLOWED', 'No analysed clips; finish analysis first.')
    policy = next((o['summary'].get('cost') and None for o in outputs if o['stage'] == 'analysis'), None)
    situation = situation_from(settings)
    doc = {'contract': 'videowizard-editing-inputs-v1', 'run_id': str(run['id']), 'binding': {'script': script['content_digest'], 'brief': brief['content_digest']},
           'accepted_inputs': {'intake': {'title': run['title']}, 'brief': brief, 'script': {'spoken_text': script['spoken_text'], 'content_digest': script['content_digest']},
                               'voice': {k: voice_o['summary'].get(k) for k in ('voice_id', 'name', 'model_id')}},
           'narration': {'id': narration['key'], 'sha256': narration['sha256'], 'size_bytes': narration['bytes'], 'mime': 'audio/mpeg', 'original_name': 'narration.mp3'},
           'narration_timing': timing, 'source_audio_policy': 'allowed' if situation['source_audio_in_output'] != 'none' else 'excluded',
           'analysis_context': {}, 'sources': sources, 'analyses': analyses, 'missing': [],
           'clocks': {'narration': 'source_seconds', 'film': 'film_frames', 'video': 'native_source_frames', 'review': 'presentation_frames'},
           'planner': 'current_chat_conversation', 'planner_api_calls': 0,
           'planning_settings': {'workflow_situation': situation, 'output': {'fps': str(settings['fps']), 'resolution': list(settings['resolution'])}},
           'evidence_use_limits': 'Retained observations keep original request bindings.'}
    return {'revision': 0, 'context_digest': digest(doc), 'document': doc, 'ready_for_planning': True, 'resolve_execution_ready': False}


# ---------- actions ----------

def prepare(conn, store, user, run, outputs, settings):
    existing = session_of(store, run, required=False)
    if existing and existing.get('draft'):
        raise Problem(409, 'NOT_ALLOWED', 'A draft exists for this run; use `vw revise --stage planning` to start over.')
    inputs = build_inputs(conn, store, run, outputs, settings)
    pack = guarded(lambda: contract.package(inputs, contract.definition()))
    pk = save_json(store, key(run, 'package.json'), pack)
    session = {'contract': 'vw2-planning-session-v1', 'settings': settings, 'inputs_digest': inputs['context_digest'], 'inputs': inputs,
               'package_key': pk['key'], 'package_digest': digest(pack), 'context_digest': pack['context_digest'],
               'scene_grouping': None, 'draft': None, 'versions': [], 'user_answers': {}, 'mechanical_answers': {}, 'frames': {}, 'jobs': {},
               'answer_review': None, 'ledger': None, 'ledger_digest': None, 'certificate': None, 'events': []}
    save_session(store, run, session)
    return {'package': pk, 'context_digest': pack['context_digest'], 'scene_grouping_required': True, 'next': 'scenes'}


def set_scenes(conn, store, user, run, scenes, quote):
    session = session_of(store, run)
    if session.get('draft'):
        raise Problem(409, 'NOT_ALLOWED', 'Scenes are frozen once a draft exists.')
    value = guarded(lambda: scenes_mod.proposal({'package': load_json(store, session['package_key'])}, session['inputs'], contract.definition(), {'scenes': scenes}))
    pack = value['package']
    pk = save_json(store, key(run, 'package.json'), pack)
    session.update(package_key=pk['key'], package_digest=digest(pack), context_digest=pack['context_digest'],
                   scene_grouping={'version': scenes_mod.VERSION, 'scenes': scenes, 'proposal_digest': value['proposal_digest'], 'quote': quote, 'by': user['id']})
    save_session(store, run, session)
    return {'package': pk, 'context_digest': pack['context_digest'], 'passages': pack['context']['passage_ids']}


def _package(store, session):
    return load_json(store, session['package_key'])


def check(store, run, plan):
    session = session_of(store, run)
    pack = _package(store, session)
    try:
        checked = contract.validate_candidate(plan, pack, presentation_preview=True)
    except (ValueError, KeyError, TypeError, ZeroDivisionError, OverflowError) as exc:
        return {'status': 'rejected', 'error': str(exc), 'plan_digest': digest(plan)}
    return {'status': checked['status'], 'presentation': checked['presentation'], 'plan_digest': checked['plan_digest'], 'sequences': len(checked['sequences'])}


def draft(conn, store, user, run, plan, quote):
    session = session_of(store, run)
    if not session.get('scene_grouping'):
        raise Problem(409, 'NOT_ALLOWED', 'Set scene groups before drafting.')
    _check_blocked(conn, run)
    pack = _package(store, session)
    result = check(store, run, plan)
    if result['status'] != 'draft_technically_valid':
        _bump(conn, run, result)
    conn.execute("delete from vw2_attempts where run_id=%s and stage=%s and unit=''", (run['id'], STAGE))
    version = len(session['versions']) + 1
    pk = save_json(store, key(run, f'plan-v{version}.json'), plan)
    entry = {'version': version, 'file': pk, 'plan_digest': digest(plan), 'ledger_digest': session.get('ledger_digest'), 'quote': quote, 'by': user['id'],
             'at': datetime.now(timezone.utc).isoformat(), 'questions': [q['id'] for q in plan.get('clarification_questions', [])]}
    session['versions'].append(entry)
    if session.get('draft') is None:
        session['draft'] = entry
        session['questions'] = deepcopy(plan.get('clarification_questions', []))
    save_session(store, run, session)
    return {'version': version, 'plan_digest': entry['plan_digest'], 'questions': entry['questions'], 'status': result['status']}


def _bump(conn, run, result):
    """A rejected draft counts as an attempt (slice-1 cap); then refuse."""
    from .analysis_jobs import connect
    st = core._stage(core.stage_table(run['procedure_version']), STAGE)
    with connect() as c:
        row = c.execute('''insert into vw2_attempts(run_id, stage, unit, count, blocked) values (%s,%s,'',1, 1 >= %s)
                           on conflict (run_id, stage, unit) do update set count = vw2_attempts.count + 1, blocked = vw2_attempts.count + 1 >= %s returning count, blocked''',
                        (run['id'], STAGE, st['cap'], st['cap'])).fetchone()
    if row['count'] > st['cap']:
        raise Problem(409, 'NEEDS_USER_DECISION', f"The plan was rejected {row['count']} times: {result['error']}", options=['retry', 'revise', 'defect', 'stop'])
    raise Problem(422, 'PLAN_REJECTED', result['error'], attempt=row['count'], cap=st['cap'])


def _check_blocked(conn, run):
    row = conn.execute("select count, blocked from vw2_attempts where run_id=%s and stage=%s and unit=''", (run['id'], STAGE)).fetchone()
    if row and row['blocked']:
        raise Problem(409, 'NEEDS_USER_DECISION', f"The plan was rejected {row['count']} times; ask the operator how to proceed.", options=['retry', 'revise', 'defect', 'stop'])


def _question(session, qid, recipient=None):
    q = next((q for q in session.get('questions') or [] if q['id'] == qid), None)
    if not q or (recipient and q['recipient'] != recipient):
        raise Problem(422, 'PLANNING_CONTRACT', f'No {recipient or ""} question {qid} in the draft.')
    return q


def answer_user(store, user, run, qid, answer, quote):
    session = session_of(store, run)
    q = _question(session, qid, 'user')
    if qid in session['user_answers']:
        raise Problem(409, 'NOT_ALLOWED', 'That question is already answered; answers are kept.')
    session['user_answers'][qid] = {'question_id': qid, 'answer': answer, 'verbatim_reply': quote, 'question_digest': digest(q), 'by': user['id']}
    save_session(store, run, session)
    return {'answered': qid}


def mechanical(check_, question, context):
    kind = check_.get('kind')
    if kind == 'source_range':
        source = context['sources'][check_['source_id']]
        native = Fraction(source['metadata']['frame_rate'])
        a, b = check_['start_frame'], check_['end_frame']
        if not (type(a) is int and type(b) is int and 0 <= a < b <= source['native_frame_count']):
            fail('Invalid requested source range.')
        result = {'start_s': float(Fraction(a) / native), 'end_s': float(Fraction(b) / native), 'duration_s': float(Fraction(b - a) / native), 'source_sha256': source['sha256']}
    elif kind == 'crop':
        source = context['sources'][check_['source_id']]
        x, y, w, h = [check_[k] for k in ('x', 'y', 'width', 'height')]
        ow, oh = context['resolution']
        if not all(type(v) is int for v in (x, y, w, h)):
            fail('Crop uses integer pixels.')
        result = {'within_source': 0 <= x and 0 <= y and w > 0 and h > 0 and x + w <= source['metadata']['width'] and y + h <= source['metadata']['height'],
                  'aspect_matches': w * oh == h * ow, 'source_sha256': source['sha256']}
    elif kind == 'narration_pause':
        words = [w for w in context['mapped_words'] if w['passage_id'] == check_['passage_id']]
        if not words:
            fail('Unknown narration passage.')
        result = {'source_boundary_s': max(w['source_end_s'] for w in words), 'narration_sha256': context['narration']['sha256']}
    else:
        fail('Use source_range, crop or narration_pause checks.')
    return {'question_id': question['id'], 'answer': json.dumps(result, sort_keys=True), 'check': deepcopy(check_), 'result': result,
            'limitations': 'Arithmetic against registered source metadata; no new viewing.'}


def answer_mechanical(store, user, run, qid, check_):
    session = session_of(store, run)
    q = _question(session, qid, 'codex')
    if qid in session['mechanical_answers']:
        raise Problem(409, 'NOT_ALLOWED', 'That check is already answered.')
    context = _package(store, session)['context']
    session['mechanical_answers'][qid] = guarded(lambda: mechanical(check_, q, context)) | {'question_digest': digest(q)}
    save_session(store, run, session)
    return session['mechanical_answers'][qid]


def extract_frames(store, user, run, qid, source_id, times):
    """Stills at requested times with ffmpeg (v1 used PyAV). Times must lie inside the question's intervals."""
    session = session_of(store, run)
    q = _question(session, qid, 'flash')
    if q['property'] not in ('contact_state', 'object_identity', 'person_hand_association'):
        fail('Use stills only for contact/position/identity; movement needs an original-video question.')
    if qid in session['frames']:
        raise Problem(409, 'NOT_ALLOWED', 'Frames were already extracted for this question.')
    context = _package(store, session)['context']
    source = context['sources'].get(source_id)
    spans = [s for s in q['inspect'] if s['source_id'] == source_id]
    if not source or not spans or not isinstance(times, list) or not 0 < len(times) <= 24 or len(set(times)) != len(times) \
            or not all(isinstance(t, (int, float)) and math.isfinite(t) and any(s['start_s'] <= t < s['end_s'] for s in spans) for t in times):
        fail('Supply 1–24 unique times inside this question interval on that source.')
    name = source['original_name']
    rows = []
    with tempfile.TemporaryDirectory(prefix='vw2-frames-') as folder:
        original = Path(folder) / 'original.mp4'
        data = store.get(f"{run['id']}/media/{name}")
        if hashlib.sha256(data).hexdigest() != source['sha256']:
            fail('Original changed before frame extraction.')
        original.write_bytes(data)
        for i, t in enumerate(times):
            out = Path(folder) / f'F{i + 1}.png'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{t:.6f}', '-i', str(original), '-frames:v', '1', str(out)], check=True, capture_output=True, timeout=120)
            png = out.read_bytes()
            fk = save_json  # placeholder to keep linters quiet
            k = key(run, f'frames/{qid}/F{i + 1}.png')
            store.put(k, png, 'image/png')
            pts = round(t * 1000)
            from PIL import Image
            from io import BytesIO
            with Image.open(BytesIO(png)) as im:
                w, h = im.size
            rows.append({'frame_id': f'F{i + 1}', 'requested_s': t, 'original_s': float(Fraction(pts, 1000)), 'pts': pts, 'stream_start_pts': 0, 'time_base': '1/1000',
                         'width': w, 'height': h, 'sha256': hashlib.sha256(png).hexdigest(), 'key': k, 'decoder': 'ffmpeg-seek'})
    manifest = {'contract': 'targeted-frames-v1', 'question_id': qid, 'question_sha256': digest(q), 'context_sha256': digest(context), 'source_id': source_id,
                'source_sha256': source['sha256'], 'frames': rows, 'coverage': 'explicit_sampled_frames_only'}
    session['frames'][qid] = {'status': 'complete', 'source_id': source_id, 'times': times, 'manifest': manifest, 'manifest_digest': digest(manifest)}
    save_session(store, run, session)
    return {'question_id': qid, 'frames': [{k: r[k] for k in ('frame_id', 'requested_s', 'key')} for r in rows]}


def inspect(conn, store, user, run, qids):
    """Queue one paid Gemini 4 Argon inspection job per routed question (≤3 sources or the extracted stills)."""
    session = session_of(store, run)
    if session.get('ledger'):
        raise Problem(409, 'NOT_ALLOWED', 'The ledger is prepared; inspections belong before it.')
    if len(session['jobs']) + len(qids) > 10:
        raise Problem(409, 'NEEDS_USER_DECISION', 'Over 10 paid inspections for this plan version.', options=['revise', 'defect', 'stop'])
    pack = _package(store, session)
    context, plan = pack['context'], load_json(store, session['draft']['file']['key'])
    created = []
    for qid in qids:
        q = _question(session, qid, 'flash')
        if qid in session['jobs']:
            continue
        frame = session['frames'].get(qid)
        sids = sorted({s['source_id'] for s in q['inspect']})
        if not 0 < len(sids) <= 3:
            fail('A question uses at most three originals.')
        prompt = ('Answer the supplied contact/position question independently for each labelled still. Return yes/no/unclear and the visible cue; do not infer movement.\nQUESTION\n' + json.dumps(q, ensure_ascii=False)) if frame \
            else pack['inspector_prompt'] + '\nFOCUSED QUESTION PACKAGE\n' + json.dumps(guarded(lambda: clar.focused_question_package(q, plan, context)), ensure_ascii=False, sort_keys=True)
        schema = _frame_schema() if frame else clar.flash_schema()
        snap = {'kind': 'inspection', 'question': q, 'question_id': qid, 'context_digest': session['context_digest'], 'draft_digest': session['draft']['plan_digest'],
                'mode': 'frames' if frame else 'video', 'prompt': prompt, 'schema': schema,
                'sources': {sid: {'name': context['sources'][sid]['original_name'], 'sha256': context['sources'][sid]['sha256']} for sid in sids},
                'frames': [{'frame_id': f['frame_id'], 'key': f['key'], 'original_s': f['original_s']} for f in frame['manifest']['frames']] if frame else [],
                'understand_audio': True}
        rk = save_json(store, key(run, f'inspection/{qid}.request.json'), snap)
        row = conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'planning',%s,'gemini',%s, gen_random_uuid()) returning id",
                           (run['id'], qid, Jsonb({'kind': 'inspection', 'question_id': qid, 'request_key': rk['key'], 'mode': snap['mode'], 'sources': snap['sources'], 'frames': snap['frames'], 'prompt_key': rk['key']}))).fetchone()
        session['jobs'][qid] = {'job_id': str(row['id']), 'status': 'queued', 'request': rk}
        created.append(qid)
    save_session(store, run, session)
    return {'queued': created}


def _frame_schema():
    return clar.obj({'frames': clar.array(clar.obj({'frame_id': clar.TEXT, 'answer': {'type': 'string', 'enum': ['yes', 'no', 'unclear']}, 'visible_cue': clar.TEXT, 'limits': clar.TEXT}))})


def refresh_jobs(conn, store, run, session):
    """Pull inspection job outcomes from vw2_jobs into the session."""
    for qid, j in session['jobs'].items():
        row = conn.execute('select status, result, error, cost from vw2_jobs where id=%s', (j['job_id'],)).fetchone()
        if row:
            j.update(status=row['status'], error=row['error'], cost=row['cost'], result=row['result'])
    return session


def status(conn, store, run):
    session = session_of(store, run, required=False)
    if not session:
        return {'state': 'not_prepared', 'next': 'prepare'}
    refresh_jobs(conn, store, run, session)
    save_session(store, run, session)
    questions = session.get('questions') or []
    pending = [q['id'] for q in questions if q['recipient'] == 'user' and q['id'] not in session['user_answers']] + \
              [q['id'] for q in questions if q['recipient'] == 'codex' and q['id'] not in session['mechanical_answers']] + \
              [q['id'] for q in questions if q['recipient'] == 'flash' and session['jobs'].get(q['id'], {}).get('status') != 'retained']
    nxt = ('scenes' if not session.get('scene_grouping') else 'draft' if not session.get('draft') else
           'answer questions' if pending else 'review' if questions and not session.get('answer_review') and any(q['recipient'] == 'flash' for q in questions) else
           'ledger' if questions and not session.get('ledger') else 'finalize' if not session.get('certificate') else 'done')
    return {'state': 'prepared', 'context_digest': session['context_digest'], 'scenes': bool(session.get('scene_grouping')), 'versions': len(session['versions']),
            'questions': questions, 'pending': pending, 'jobs': {k: {kk: v.get(kk) for kk in ('job_id', 'status', 'error', 'cost')} for k, v in session['jobs'].items()},
            'ledger_digest': session.get('ledger_digest'), 'certificate': session.get('certificate'), 'next': nxt}


def inspector_response(session):
    answers, limits = [], []
    for q in session.get('questions') or []:
        if q['recipient'] != 'flash':
            continue
        job = session['jobs'].get(q['id']) or {}
        if job.get('status') != 'retained':
            fail('Wait for or recover the retained inspector responses first.')
        answers.extend(deepcopy(job['result']['answer']['answers']))
        limits.append(job['result']['answer']['inspection_limits'])
    return {'answers': answers, 'inspection_limits': '\n'.join(limits) if limits else 'No fresh inspection.'}


def prose_fields(value, path=''):
    if isinstance(value, str):
        return {path: value}
    rows = {}
    if isinstance(value, dict):
        for k, v in value.items():
            rows.update(prose_fields(v, path + '/' + str(k)))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            rows.update(prose_fields(v, path + '/' + str(i)))
    return rows


def review_input(conn, store, run):
    session = refresh_jobs(conn, store, run, session_of(store, run))
    response = guarded(lambda: inspector_response(session))
    return {'response': response, 'response_digest': digest(response), 'fields': [{'path': p, 'value_digest': digest(v), 'text': v} for p, v in prose_fields(response).items()]}


def review_answers(conn, store, user, run, document):
    session = refresh_jobs(conn, store, run, session_of(store, run))
    response = guarded(lambda: inspector_response(session))
    if document.get('response_digest') != digest(response):
        fail('Bind the review to the exact retained answer fields (response_digest).')
    session['answer_review'] = deepcopy(document)
    save_session(store, run, session)
    return {'reviewed': len(document.get('fields', []))}


def ledger(conn, store, user, run):
    session = refresh_jobs(conn, store, run, session_of(store, run))
    if not session.get('draft'):
        raise Problem(409, 'NOT_ALLOWED', 'Draft first.')
    context = _package(store, session)['context']
    plan = load_json(store, session['draft']['file']['key'])
    questions = session.get('questions') or []
    response = guarded(lambda: inspector_response(session))
    result = guarded(lambda: clar.ledger(plan, questions, response, list(session['user_answers'].values()), list(session['mechanical_answers'].values()), context))
    fields = prose_fields(response)
    audit = session.get('answer_review')
    if response['answers']:
        if not audit or audit.get('response_digest') != digest(response):
            fail('Review all inspector answer fields before the ledger.')
        rows = audit.get('fields', [])
        if len(rows) != len(fields) or {r.get('path') for r in rows} != set(fields):
            fail('Review every retained inspector string field once.')
        for row in rows:
            if row.get('value_digest') != digest(fields[row['path']]) or row.get('scope') not in ('inside_target', 'outside_target_excluded', 'uncertain', 'metadata') or not str(row.get('reason', '')).strip():
                fail('Answer field review must bind exact values with a scope and reason.')
        excluded = audit.get('excluded_observation_ids', [])
        for observation in result['observations']:
            if observation['id'] in excluded:
                observation.update(usable_for_target=False, scope_status='semantic_scope_excluded')
        result['answer_field_review'] = deepcopy(audit)
    frame_rows = []
    for qid, job in session['jobs'].items():
        for frame in (job.get('result') or {}).get('frames', []):
            q = _question(session, qid)
            frame_rows.append({**deepcopy(frame), 'id': qid + ':frame:' + frame['frame_id'], 'question_id': qid, 'sequence_id': q['sequence_id'], 'shot_id': q['shot_id'],
                               'property': q['property'], 'source_id': session['frames'][qid]['source_id']})
    result.update(frame_results=frame_rows, frame_artifacts={}, context_digest=session['context_digest'], draft_digest=session['draft']['plan_digest'])
    lk = save_json(store, key(run, 'ledger.json'), result)
    session.update(ledger=lk, ledger_digest=digest(result))
    save_session(store, run, session)
    return {'ledger': lk, 'ledger_digest': session['ledger_digest'], 'observations': len(result['observations'])}


def revise(conn, store, user, run, plan, quote):
    session = session_of(store, run)
    if not session.get('draft'):
        raise Problem(409, 'NOT_ALLOWED', 'Draft first.')
    if session.get('questions') and not session.get('ledger'):
        raise Problem(409, 'NOT_ALLOWED', 'Prepare the ledger before revising.')
    if session.get('certificate'):
        raise Problem(409, 'NOT_ALLOWED', 'Finalized; use `vw revise --stage planning` to reopen.')
    _check_blocked(conn, run)
    result = check(store, run, plan)
    if result['status'] != 'draft_technically_valid':
        _bump(conn, run, result)
    if guarded(lambda: clar.validate_questions(plan, _package(store, session)['context'])):
        fail('A revision may not add new questions; resolve them in the next planning round.')
    version = len(session['versions']) + 1
    pk = save_json(store, key(run, f'plan-v{version}.json'), plan)
    session['versions'].append({'version': version, 'file': pk, 'plan_digest': digest(plan), 'ledger_digest': session.get('ledger_digest'), 'quote': quote, 'by': user['id'],
                                'at': datetime.now(timezone.utc).isoformat(), 'questions': []})
    save_session(store, run, session)
    return {'version': version, 'plan_digest': digest(plan)}


def _components(plan, review, context, evidence):
    expected = {(sid, s['id']): s for sid, seq in clar.sequences(plan) for s in seq['shots'] if s['kind'] == 'video'}
    entries = review.get('component_reviews', [])
    keys = [(e.get('sequence_id'), e.get('shot_id')) for e in entries]
    if len(keys) != len(set(keys)) or set(keys) != set(expected):
        fail('Review every selected video shot exactly once, including alternatives: ' + ', '.join(f'{a}:{b}' for a, b in sorted(set(expected) - set(keys))))
    observations = {r['id']: r for r in evidence['observations'] if r.get('usable_for_target')}
    frames = {r['id']: r for r in evidence['frame_results']}
    registry = context['evidence_registry']
    for entry in entries:
        k = (entry['sequence_id'], entry['shot_id'])
        shot = expected[k]
        sid = shot['source_id']
        native = Fraction(context['sources'][sid]['metadata']['frame_rate'])
        a, b = float(Fraction(shot['source_start_frame']) / native), float(Fraction(shot['source_end_frame']) / native)
        if set(entry.get('components', {})) != set(COMPONENTS):
            fail('All six component judgments are required.')
        for name, part in entry['components'].items():
            if part.get('status') not in ('supported', 'uncertain', 'contradicted', 'not_applicable') or type(part.get('relied_on')) is not bool or not str(part.get('reason', '')).strip() or not isinstance(part.get('evidence_refs'), list):
                fail(f'Component {name} of {k[1]} needs status, relied_on, reason and evidence_refs.')
            for ref in part['evidence_refs']:
                if ref == 'context':
                    if name not in ('timestamp_mapping', 'question_scope'):
                        fail('Context arithmetic is not perceptual evidence.')
                elif ref == f'plan:{k[0]}:{k[1]}':
                    if name != 'question_scope':
                        fail('Plan choices are not visible action evidence.')
                elif ref in registry:
                    origin = context['evidence_references'][ref]
                    if origin['source_id'] != sid:
                        fail('Component source differs from the selected shot.')
                    span = registry[ref].get('interval')
                    if span and min(span['end_s'], b) <= max(span['start_s'], a):
                        fail('Component evidence is outside the selected excerpt.')
                    if part['relied_on'] and name not in ('timestamp_mapping', 'question_scope') and origin['collection'] not in ('visual_events', 'visible_text', 'entities'):
                        fail('Interpretation or speech alone cannot prove a visible property.')
                elif ref in observations:
                    row = observations[ref]
                    o = row['observation']
                    if (row['sequence_id'], row['shot_id']) != k or row['property'] != name or o['source_id'] != sid or min(o['end_s'], b) <= max(o['start_s'], a):
                        fail('Clarification evidence cannot transfer to another decision, property or excerpt.')
                elif ref in frames:
                    row = frames[ref]
                    if (row['sequence_id'], row['shot_id']) != k or row['source_id'] != sid or not a <= row['original_s'] < b or name not in ('object_identity', 'person_hand_association', 'contact_state', 'timestamp_mapping', 'question_scope'):
                        fail('Frame evidence does not match this shot, excerpt or property.')
                    if part['relied_on'] and row['answer'] == 'unclear':
                        fail('Unclear sampled answers cannot support a relied-on claim.')
                else:
                    fail('Unknown, excluded or self-declared evidence reference: ' + str(ref))
            if part['relied_on'] and not (part['status'] == 'supported' and part['evidence_refs']):
                fail('A relied-on component requires supported retained evidence.')


def finalize(conn, store, user, run, review, quote):
    session = refresh_jobs(conn, store, run, session_of(store, run))
    if session.get('certificate'):
        raise Problem(409, 'NOT_ALLOWED', 'Already finalized.')
    if not session.get('versions'):
        raise Problem(409, 'NOT_ALLOWED', 'Draft first.')
    pack = _package(store, session)
    context = pack['context']
    selected = session['versions'][-1]
    original = load_json(store, selected['file']['key'])
    questions = session.get('questions') or []
    if questions:
        if not session.get('ledger'):
            raise Problem(409, 'NOT_ALLOWED', 'Questions exist: prepare the ledger and revise before finalizing.')
        if len(session['versions']) < 2:
            raise Problem(409, 'NOT_ALLOWED', 'Questions exist: a revision after the ledger is required.')
        evidence = load_json(store, session['ledger']['key'])
    else:
        evidence = {'observations': [], 'frame_results': []}
    if guarded(lambda: clar.validate_questions(original, context)):
        fail('New unanswered questions remain pending; resolve them before finalizing.')
    plan, supplemental = clar.separate_supplemental_notes(original)
    guarded(lambda: contract.validate_candidate(plan, pack))
    ledger_digest = session.get('ledger_digest') or digest(evidence)
    if review.get('plan_digest') != digest(plan) or review.get('context_digest') != session['context_digest'] or review.get('ledger_digest') != ledger_digest:
        fail(f"The assessment must bind plan_digest {digest(plan)[:12]}…, context_digest {session['context_digest'][:12]}… and ledger_digest {ledger_digest[:12]}….")
    if not all(review.get(k) is True for k in FLAGS) or not str(review.get('assessment', '')).strip() or not review.get('remaining_limitations') \
            or review.get('unresolved_relied_on_claims') != []:
        fail('Assessment needs all seven flags true, an assessment text, at least one remaining limitation and no unresolved relied-on claims.')
    _components(plan, review, context, evidence)
    certificate = {'contract': 'videowizard-execution-review-v1', 'context_digest': session['context_digest'], 'plan_digest': digest(plan), 'ledger_digest': ledger_digest,
                   'version': selected['version'], 'fps': context['fps'], 'resolution': context['resolution'], 'duration_frames': plan['duration_frames'],
                   'gaps': [{'shot_id': s['id'], 'start_frame': s['timeline_start_frame'], 'end_frame': s['timeline_end_frame'], 'passage_ids': s['passage_ids'], 'reason': s['reason']}
                            for s in plan['shots'] if s['kind'] == 'gap'],
                   'provisional_execution_ready': True, 'final_film_approved': False}
    handoff = guarded(lambda: execution_document({'selected_plan': plan, 'package': pack, 'certificate_digest': digest(certificate)}))
    handoff['narration_pieces'] = frame_aligned_pieces(handoff, context)
    files = {'plan.json': save_json(store, key(run, 'plan.json'), plan), 'assessment.json': save_json(store, key(run, 'assessment.json'), review),
             'ledger.json': save_json(store, key(run, 'ledger.json'), evidence), 'package.json': {'key': session['package_key'], **_sha(store, session['package_key'])},
             'certificate.json': save_json(store, key(run, 'certificate.json'), certificate), 'handoff.json': save_json(store, key(run, 'handoff.json'), handoff)}
    for name, f in files.items():
        jobs.record_file(conn, run['id'], STAGE, f['key'], name, f['sha256'], f['bytes'], 'application/json')
    session.update(certificate=certificate, certificate_digest=digest(certificate), quote=quote)
    save_session(store, run, session)
    refs = [{'name': n, 'key': f['key'], 'sha256': f['sha256'], 'bytes': f['bytes'], 'location': 'storage', 'receipt': True} for n, f in files.items()]
    inspection_cost = [j.get('cost') for j in session['jobs'].values() if j.get('cost')]
    out = core.output(conn, user, run, {'stage': STAGE, 'files': refs, 'accepted_quote': quote,
                                        'summary': {**certificate, 'units': {'visuals': [g['shot_id'] for g in certificate['gaps']]}, 'versions': len(session['versions']), 'questions': len(questions), 'inspections': len(session['jobs']),
                                                    'inspection_cost': inspection_cost, 'supplemental_notes': len(supplemental.get('supplemental_notes', []))}})
    return {'certificate': certificate, 'output': str(out['id'])}


def _sha(store, k):
    data = store.get(k)
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def frame_aligned_pieces(handoff, context):
    """Narration pieces cut on whole output frames so the Mac timeline never rounds a spoken boundary (v1 open defect)."""
    fps = Fraction(context['fps'])
    pieces = []
    for seg in handoff['sequences'][0]['compiled']['audio_segments']:
        start_f = math.floor(Fraction(str(seg['timeline_start_s'])) * fps)
        end_f = math.ceil(Fraction(str(seg['timeline_end_s'])) * fps)
        pieces.append({'id': seg['id'], 'source_start_s': seg['source_start_s'], 'source_end_s': seg['source_end_s'],
                       'timeline_start_frame': start_f, 'timeline_end_frame': end_f,
                       'timeline_start_s': float(Fraction(start_f) / fps), 'timeline_end_s': float(Fraction(end_f) / fps)})
    return pieces
