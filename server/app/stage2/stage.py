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

from .. import core, film, jobs, runlog
from ..clip_log import solver
from ..errors import Problem
from . import CONTRACT_MASTER, CONTRACT_OPTIONS, SLATE_FRAMES, ledger as LG, looks, narration as NR, package as P, review as RV, slides as SL, validator as V

def timeline(run):
    """design/139 R1: the cut's timeline from the operator's recorded shape and rate; a film from before keeps 1920 x 1080 at 25."""
    t = film.timeline(run)
    return {k: t[k] for k in ('width', 'height', 'fps')}
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

def cut_log(run, doc, version):
    """design/142 R1, R2: one log entry per blank (the clips considered and why) and per shot chosen over its alternatives."""
    out = []
    for o in doc.get('options') or []:
        for i, ev in enumerate(o.get('events') or [], 1):
            about = f"{o.get('beat_id')} event {i}"
            if ev.get('blank'):
                why = '; '.join(f"{c['sub_clip_id']}: {c['why']}" + (f" ({c['words']})" if c.get('words') else '') for c in ev.get('considered') or []) or f"none fit: {ev.get('none_fit')}"
                out.append({'kind': 'blank', 'about': about, 'entry': f"blank of {ev.get('timeline_frames')} frames for {ev.get('intent')!r}; considered: {why}"})
            elif ev.get('preferred_because'):
                alts = ', '.join(a.get('sub_clip_id') or '' for a in ev.get('alternatives') or [])
                out.append({'kind': 'choice', 'about': about, 'entry': f"{ev.get('sub_clip_id')} chosen over {alts}: {ev['preferred_because']}"})
    return [{**e, 'run_id': run['id'], 'stage': 'options', 'rule': f'options v{version} (design/142 R2)', 'by_kind': 'assistant', 'by_name': '', 'quote': '', 'request_id': None} for e in out]


def clip_key(run, clip):
    """design/147 L3: where a clip's media is: a library clip carries the key of its source film; this film's own clips live under the run."""
    return clip.get('key') or f"{run['id']}/media/{clip['name']}"


def skipped_note(run):
    """Defect 49 follow-up (VW-22, 12 Nov 2026): what the assistant is told when clips were skipped at the analysis because the client's library holds
    them. Without it the assistant read the thin coverage as lost footage and offered the operator a paid analysis or blanks; both are wrong."""
    n = len((run.get('film') or {}).get('library_skipped') or [])
    if not n:
        return {}
    return {'library_skipped': f"{n} of this film's clips were skipped at the analysis because the client's library already holds them. They are not lost and need no new "
                               "analysis: the library round (`vw options library`) offers every one of them, generic or not, with its description, at no cost. A stored study says "
                               "which lines of ITS film a clip fitted, not of this one, so these clips carry no line fits and the coverage figures here do not count them: match them "
                               "to the scenes by their descriptions in that round. Never offer the operator a paid analysis of them, and never treat their scenes as blanks before the library round."}


def library(conn, store, user, run, outputs):
    """design/147 L4: the library round, after the second look; one flow for the tool and a page."""
    from .. import brandlib
    session = session_of(store, run)
    # defect 61: the file is written again with the library rows, so the record keeps its new size and fingerprint (the plan's digest stays as prepare set it)
    out = brandlib.library_round(conn, store, run, outputs, session, lambda pk: session['package'].update(save_json(store, key(run, 'package.json'), pk)))
    save_session(store, run, session)
    return out


CHAPTERS_UNKNOWN = ('`chapters_unknown` lists the chapter names the clip studies carry that are not chapters of this film (a study reused from another film keeps '
                    "that film's names); their pieces fit no scene by chapter until the scenes file maps them. Add `chapter_map` to out/scenes.json: each name with the chapter of "
                    'this film that shows the same thing (`nearest` is a hint, not an answer), or "" when none does; show the map to the operator with the scenes.')


def need_scenes(approved, words=None, process_stages=None, unknown=None):
    """design/139 R4 (SK, 2 Nov 2026, design/138 A6): the cut waits for a scene split the operator approved; it is never one scene per paragraph.
    Defect 53 (VW-24, 15 Nov 2026): a scene names its first word by its id, and the ids were only in the options files, which exist after this
    step has prepared. The refusal now carries what a scene split is made from: every sentence with the id of its first word, the shape of the
    scenes file, and the brief's chapters."""
    if not approved:
        extra = {}
        if words:
            extra = {'sentences': [{'first_word_id': words[a]['id'], 'last_word_id': words[b]['id'], 'text': ' '.join(w['text'] for w in words[a:b + 1])} for a, b in NR.sentence_ranges(words)],
                     'shape': P.SCENES_SHAPE, 'process_stages': list(process_stages or []), **({'chapters_unknown': unknown} if unknown else {})}
        raise Problem(422, 'SCENES_NOT_APPROVED', 'No scene split is approved yet. A scene starts at the first word of a sentence: `sentences` in this answer lists every sentence '
                      'with the id of its first word (first_word_id) and of its last (for a pause after it), `shape` is the form of out/scenes.json, and `process_stages` '
                      'are the brief\'s chapters. Propose the scenes to the operator, write out/scenes.json, record it with '
                      '`vw options scenes --file out/scenes.json --quote "<their words>"`, then prepare again.' + (' ' + CHAPTERS_UNKNOWN if unknown else ''), **extra)
    return approved


def learned_rules(conn, run):
    return core.client_rules(conn, run.get('client_id') or '')   # one source for every stage (design/37 2.7)


def prepare(conn, store, user, run, outputs):
    from .. import brandlib
    none = film.footage(run) == 'none'   # SK, 23 Nov 2026: a film with no camera footage of its own has no clip to study and none to mark
    if not none:
        brandlib.need_marked(run)   # design/147 L1: a new film's first cut waits for the brand-generic answer; films from before skip it
    procedure = core.procedure_for(run, 'options')
    brief_o, script_o, voice_o, media_o = (_output(outputs, s) for s in ('brief', 'script', 'voice', 'media'))
    brief, _ = _file(store, brief_o, 'brief.json')
    script, _ = _file(store, script_o, 'script.json')
    timing, _ = _file(store, voice_o, 'timing.json')
    production = brief_o['summary'].get('production') or {}
    beats = script.get('beats') or []
    if not beats:
        fail('The script has no beats; re-record the script on this build.')
    session = session_of(store, run, create=True)
    words = timing['words']
    clips = {c['id']: c for c in media_o['summary']['clips']}
    cards, rows, landmarks, entities, policy, identities, other_count = [], [], set(), [], None, [], []
    from ..analysis import sentence_beats
    spoken_script = [b['text'] for b in sentence_beats(script)]   # the sentences the clip study numbered
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
        if log.get('sub_clips'):   # SK, 23 Nov 2026 (VW-25): which pieces are allowed is the server's own rule and costs nothing; a stored study is judged by today's rule, under the policy it was studied with
            solver.solve(log, (log['sub_clips'][0].get('stage15') or {}).get('policy') or doc['identity'].get('speaker_policy') or {}, clip, timeline(run))
        policy = policy or (doc['identity'].get('speaker_policy') or {})
        identities.append(doc['identity'])
        by_sentence = P.study_sentences(doc['identity'], len(spoken_script))   # design/193; 0 for a study of another count of sentences (23 Nov 2026)
        if doc['identity'].get('fit_unit') == 'sentence' and not by_sentence:
            other_count.append(clip['name'])
        cards.append({'clip_id': clip['id'], 'clip_name': clip['name'], 'descriptive_name': log.get('descriptive_name'), 'lines': log.get('summary_card_lines') or []})
        for sub in log.get('sub_clips') or []:
            rows.append(P.sub_clip_row(clip, log, sub, timeline(run)['fps'], by_sentence))
            landmarks.update((sub.get('continuity_and_story') or {}).get('world_landmarks_and_props') or [])
        entities.extend({'clip_id': clip['id'], **e} for e in log.get('entities') or [])
    if not rows and not none:
        raise Problem(409, 'NOT_ALLOWED', 'No analysed clips; run analysis first.')
    if none and policy is None:   # no clip log carries the policy: nobody is filmed and no camera sound exists (the library round re-checks its pieces under it)
        from .. import analysis
        policy = analysis.speaker_policy(media_o['summary'], production)
    grouped = looks.groups({o['unit']: o['summary'].get('look') for o in outputs if o['stage'] == 'analysis' and o['unit'] is not None and not o['summary'].get('excluded')})
    for r in rows:   # design/142 R5: the colour group is the server's own measure, not the analysis's label
        r['color_group'] = grouped.get(r['clip_id'])
    stages = production.get('process_stages') or []
    unknown = P.apply_chapter_map(rows, stages, ((session.get('scenes') or {}).get('document') or {}).get('chapter_map') or {})   # 23 Nov 2026 (VW-25): a reused study carries another film's chapter names
    approved = need_scenes(session.get('scenes'), words, stages, unknown)
    duration = voice_o['summary'].get('duration_s') or timing['audio']['duration_s']
    try:
        plan, to_tl = NR.plan(words, duration, timeline(run)['fps'], approved['document'].get('pauses') or [])
        windows = NR.beats(words, approved['document']['scenes'], plan, to_tl, timeline(run)['fps'])
    except ValueError as exc:
        fail(exc)
    narration = {**plan, 'scenes_approved': bool(approved), 'words': NR.word_rows(words, timeline(run)['fps'], to_tl),
                 'sentences': NR.sentences(words, timeline(run)['fps'], to_tl), 'silences': NR.silences(words, timeline(run)['fps'], to_tl, plan['total_frames']),
                 'pause_rules': {'only_after_sentence_end': True, 'max_seconds': NR.MAX_PAUSE_S, 'seconds_means': 'total silence wanted; the recording\'s own gap counts toward it'}}
    unit, fit_note = P.fit_unit(identities)   # design/193: by sentence only when every clip was studied so
    if unit == 'sentence':   # 23 Nov 2026 (VW-25): the script's sentences are paired with the narration's by their words; a count difference costs no other sentence its fits
        pair = P.pair_sentences(spoken_script, [s['text'] for s in narration['sentences']])
        fit_note = P.pairing_note(spoken_script, len(narration['sentences']), pair, [f for r in rows for f in r.get('sentence_fits') or []], other_count)
        P.scene_fits_by_sentence(rows, windows, narration['sentences'], pair)
    else:
        for r in rows:   # by paragraph: a sentence number means nothing here
            r.pop('sentence_fits', None)
            r.pop('fit_lines_unread', None)
    if unit != 'sentence' and approved:   # design/125 P8: the logs know the script's paragraphs; each is mapped to the approved scenes its words fall in, beside the chapter
        at = {w['id']: w for w in narration['words']}
        paragraphs = {}
        for b in beats:
            own = [w['id'] for w in words if w.get('passage_id') == b.get('passage_id')]
            if own:
                paragraphs[b['beat_id']] = (at[own[0]]['start_frame'], at[own[-1]]['end_frame'])
        P.scene_fits(rows, windows, paragraphs)
    rules = core.effective_rules(conn, run, outputs)['learned']   # design/37 2.7
    pk = P.build(run, production, windows, cards, rows, landmarks, entities, rules, timeline(run), policy or {}, procedure.get('prompt') or '', narration)
    saved = save_json(store, key(run, 'package.json'), pk)
    session['package'] = {**saved, 'digest': digest({k: pk[k] for k in ('beats', 'sub_clips', 'timeline', 'policy', 'narration')}), 'beats': windows, 'timeline': timeline(run), 'policy': policy or {},
                          'narration_key': next(f['key'] for f in voice_o['files'] if f['name'] == 'narration.mp3'), 'clips': {c['id']: c for c in media_o['summary']['clips']},
                          'narration': {k: plan[k] for k in ('pieces', 'total_frames', 'fps', 'cuts')}}
    save_session(store, run, session)
    eligible = sum(1 for r in rows if r['eligibility'].startswith('ELIGIBLE'))
    return {'package': saved, 'beats': len(windows), 'clips': len(cards), 'sub_clips': len(rows), 'eligible_sub_clips': eligible, 'coverage': pk['coverage'],
            'learned_rules': len(rules), 'scenes_approved': bool(approved), 'pauses': len(plan['cuts']), 'sentences': len(narration['sentences']),
            **({'fit_note': fit_note} if fit_note else {}), **({'chapters_unknown': unknown, 'chapters_note': CHAPTERS_UNKNOWN + ' Then record the scenes again.'} if unknown else {}), **skipped_note(run), 'next': prepare_next(bool(approved))}


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
        document = {**document, 'scenes': NR.normalise_scenes(document.get('scenes')), 'chapter_map': P.chapter_map_of(document, stages)}
        NR.validate_scenes(words, document.get('scenes'), stages)
        intake_o = next((o for o in outputs if o['stage'] == 'intake' and o['unit'] is None), None)
        NR.scenes_cover(document.get('scenes'), stages, document.get('dropped_chapters'), ((intake_o or {}).get('summary') or {}).get('intended_visuals'))   # design/142 R8, R9
        plan, to_tl = NR.plan(words, duration, timeline(run)['fps'], document.get('pauses') or [])
        bs = NR.beats(words, document['scenes'], plan, to_tl, timeline(run)['fps'])
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        fail(exc)
    session = session_of(store, run, create=True)
    version = (session.get('scenes') or {}).get('version', 0) + 1
    record = {'version': version, 'document': {'scenes': document['scenes'], 'pauses': document.get('pauses') or [], 'dropped_chapters': document.get('dropped_chapters') or [], 'chapter_map': document['chapter_map']}, 'quote': quote, 'by': user['id'],
              'at': datetime.now(timezone.utc).isoformat()}
    saved = save_json(store, key(run, f'scenes-v{version}.json'), record)
    session['scenes'] = {**record, 'file': saved, 'digest': digest(record['document'])}
    session['current'] = None          # options built on the old beats no longer apply
    session['accepted'] = None
    session['renders'].pop('review', None)
    save_session(store, run, session)
    out = prepare(conn, store, user, run, outputs)
    if film.footage(run) == 'none':
        out = {**out, **_no_footage_cut(conn, store, user, run, outputs, quote)}
    return {**out, 'scenes': [{k: b[k] for k in ('beat_id', 'title', 'target_beat_frames', 'process_stages')} | {'seconds': round(b['target_beat_frames'] / timeline(run)['fps'], 2),
                                                                                                                  'pauses': [{'after_word_id': p['after_word_id'], 'inserted_s': round(p['inserted_frames'] / timeline(run)['fps'], 2)} for p in b['pauses']]}
                                for b in bs],
            'film_seconds': round(plan['total_frames'] / timeline(run)['fps'], 2), 'inserted_seconds': round(plan['inserted_frames'] / timeline(run)['fps'], 2)}   # design/126 OP2: a scene lists every chapter its paragraph covers; no warning


NO_FOOTAGE = 'this film has no camera footage of its own'
LIBRARY_NEXT = ("the client's library holds pieces this film may use: `vw options library` lists them with what each shows. Author out/options.json (shape in shapes.json) with a "
                'library piece only where it truly shows the words; every other scene is one blank with `none_fit`. Then `vw options check`, `vw options propose`, the review film and '
                'the master as their answers say.')


def blank_options(pk):
    """SK, 23 Nov 2026: the cut of a film with no clip at all, as the options contract wants it: every scene one blank for the visuals stage."""
    return {'contract': CONTRACT_OPTIONS, 'qc_self': {f'Q{i}': {'pass': True, 'evidence': NO_FOOTAGE} for i in range(1, 9)},
            'options': [{'option_number': i + 1, 'beat_id': bt['beat_id'], 'reasoning': NO_FOOTAGE, 'log_fields_cited': ['none'], 'best_unchosen': {'sub_clip_id': '', 'rule': NO_FOOTAGE},
                         'events': [{'blank': True, 'timeline_frames': bt['target_beat_frames'], 'intent': bt.get('title') or '', 'none_fit': NO_FOOTAGE}]} for i, bt in enumerate(pk['beats'])]}


def _no_footage_cut(conn, store, user, run, outputs, quote):
    """SK, 23 Nov 2026: what follows the approved scenes on a film with no camera footage. The client's library has pieces this film can use:
    the cut goes the usual way with them (authored, checked, watched, approved). It has none: the server writes the cut itself, every scene one
    stretch for the visuals stage, and records the options, the master and the first cut with the operator's words on the scenes; no film is
    rendered and none is watched, since it would show only cards. One flow for the tool and a page: both record scenes through `set_scenes`."""
    found = library(conn, store, user, run, outputs).get('candidates') or []
    if found:
        return {'library': {'pieces': len(found), 'clips': sorted({c['clip_name'] for c in found if c.get('clip_name')})}, 'next': LIBRARY_NEXT}
    propose(conn, store, user, run, blank_options(_package(store, session_of(store, run))))
    session = session_of(store, run)
    doc, entry = current(store, session)
    at = datetime.now(timezone.utc).isoformat()
    for sl in _slides(store, session, doc, entry):
        if _answerable(sl):
            session['decisions'][str(sl['no'])] = {'action': 'KEEP', 'type': sl['type'], 'note': NO_FOOTAGE, 'by': 'server', 'at': at}
    save_session(store, run, session)
    record_options(conn, store, user, run, quote, {'how': 'no_footage'}, film_needed=False)
    build_master(conn, store, user, run)
    rec = record_master(conn, store, user, run, quote, film_needed=False)
    return {'first_cut': 'written', 'gaps': rec['gaps'],
            'next': 'The server wrote the first cut: every scene is one stretch for the visuals stage, and the options, the master and the first cut are recorded with these words. '
                    'Nothing is rendered or watched. Next: visuals (`vw next`).'}


def _film_less(run):
    if film.footage(run) != 'none':
        raise Problem(409, 'NOT_ALLOWED', 'A first cut is recorded with its film; only a film with no camera footage of its own is recorded without one, by the server.')


def coverage(store, run):
    session = session_of(store, run)
    return {'coverage': load_json(store, session['package']['key'])['coverage'], 'beats': session['package']['beats'], **skipped_note(run)}


def _package(store, session):
    return load_json(store, session['package']['key'])


def check(store, run, doc):
    session = session_of(store, run)
    pk = _package(store, session)
    if doc.get('contract') != CONTRACT_OPTIONS:
        return {'status': 'rejected', 'refusals': [f"contract must be {CONTRACT_OPTIONS}"], 'flags': []}
    work = deepcopy(doc)
    result = V.validate_options(work, pk, session['package']['policy'])
    result['refusals'] += V.cut_reasons(doc, {r['sub_clip_id']: r for r in pk['sub_clips']})   # design/142 R2: every new proposal carries its reasons
    out = {'status': 'rejected' if result['refusals'] else 'valid', 'refusals': result['refusals'],
           **V.answer_flags(result['flags']), 'flags_total': len(result['flags'])}   # design/125 P11
    if not result['refusals']:
        out['scenes'] = SL.scene_summary(work, pk, timeline(run)['fps'])
    return out


def options_sha(options):
    """design/129 P4: the options' fingerprint, the same as the vw tool's `options_sha` at the join."""
    return hashlib.sha256(json.dumps(options, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def second_look_record(doc):
    """design/129 P4: the second look's record as the tool wrote it at the join, kept as far as it reads (never a refusal), lists capped;
    `edited_after` when the options proposed are not the ones joined. None when the cut carries no record."""
    sl = doc.get('second_look')
    if not isinstance(sl, dict):
        return None
    words = lambda v, n=300: str(v)[:n]
    names = lambda v: [words(x, 80) for x in v[:60]] if isinstance(v, list) else []
    try:
        scenes = int(sl.get('scenes') or 0)
    except (TypeError, ValueError):
        scenes = 0
    unchanged = {words(k, 80): words(v) for k, v in list(sl.get('unchanged').items())[:60]} if isinstance(sl.get('unchanged'), dict) else {}
    fixes = [{'scene': words(f.get('scene', ''), 80), 'option': f.get('option') if isinstance(f.get('option'), int) else None, 'why': words(f.get('why', ''))}
             for f in (sl.get('fixes') if isinstance(sl.get('fixes'), list) else [])[:200] if isinstance(f, dict)]
    return {'at': words(sl.get('at', ''), 40), 'scenes': scenes, 'changed': names(sl.get('changed')), 'unchanged': unchanged, 'no_fix_file': names(sl.get('no_fix_file')),
            'fixes': fixes, 'edited_after': sl.get('joined_sha') != options_sha(doc.get('options') or [])}


def propose(conn, store, user, run, doc):
    session = session_of(store, run)
    if not session.get('scenes'):   # design/43 7.3: titles, chapters and pauses are approved before any option
        raise Problem(409, 'NOT_ALLOWED', 'Propose the scenes first (`vw options scenes --file out/scenes.json --quote "…"`).')
    _check_blocked(conn, run, 'options')
    pk = _package(store, session)
    if doc.get('contract') != CONTRACT_OPTIONS:
        _bump(conn, run, 'options', [f'contract must be {CONTRACT_OPTIONS}'])
    second = second_look_record(doc)   # design/129 P4: kept beside the version, never in the cut's fingerprint
    work = deepcopy(doc)
    work.pop('second_look', None)
    result = V.validate_options(work, pk, session['package']['policy'])
    result['refusals'] += V.cut_reasons(doc, {r['sub_clip_id']: r for r in pk['sub_clips']})   # design/142 R2
    if result['refusals']:
        LG.write(None, run, len(session['versions']) + 1, LG.refusal_rows(pk, result['refusals']))   # its own connection: the request's is rolled back
        _bump(conn, run, 'options', result['refusals'])
    for o in work['options']:
        for ev in o['events']:
            ev['timeline_frames'] = ev.pop('_timeline_frames')
            ev['fps_ratio'] = ev.pop('_fps_ratio')
    slides = SL.slides(work, pk, timeline(run)['fps'])
    scenes = SL.scene_summary(work, pk, timeline(run)['fps'])
    version = len(session['versions']) + 1
    record = {'run_id': str(run['id']), 'version': version, 'package_digest': session['package']['digest'], 'document': work, 'flags': result['flags'], 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    saved = save_json(store, key(run, f'options-v{version}.json'), record)
    identity = digest(work)
    session['versions'].append({'version': version, 'file': saved, 'digest': identity, 'flags': result['flags'], 'options': len(work['options']), 'gaps': [],   # design/129 old way 10: a declared gap is refused at propose (design/125 P13)
                                'slides': slides, 'scenes': scenes, 'second_look': second})
    LG.write(conn, run, version, LG.rows(pk, work))   # the clip ledger, builder only: why each piece was or was not used
    session['current'] = identity
    session['accepted'] = None
    session['decisions'] = {}
    session['master'] = None
    session['renders'].pop('review', None)
    conn.execute("delete from vw2_attempts where run_id=%s and stage='options' and unit=%s", (run['id'], core.UNIT_NONE))
    for e in cut_log(run, work, version):   # design/142 R1: the cut's own reasons, in the run's decision log
        runlog.write(conn, e)
    save_session(store, run, session)
    return {'version': version, 'digest': identity, 'options': len(work['options']), 'gaps': session['versions'][-1]['gaps'],
            **V.answer_flags(result['flags']), 'flags_total': len(result['flags']), 'scenes': scenes,
            'slides': [{k: s.get(k) for k in ('no', 'type', 'title', 'b_roll', 'note', 'of', 'flags') if s.get(k) is not None} | {'seconds': round(s['frames'] / timeline(run)['fps'], 2)} for s in slides],   # defect 47
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
        raise Problem(409, 'NOT_ALLOWED', f"Version {entry['version']} has no stored slides (proposed in an older form): `vw options check` and `propose` again.")
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


def still_times(a, z, step, fps=25):
    """design/142 R6: the stills of a shot as cut, from a to z seconds: its first frame, one every `step` seconds, its middle and its last frame."""
    last = round(z - 1 / float(fps), 3)
    times = {round(a, 3), round((a + z) / 2, 3), last}
    t = a
    while t < last - 1e-6:
        times.add(round(t, 3))
        t += step
    return sorted(x for x in times if a - 1e-6 <= x <= last + 1e-6)


def stills(store, user, run, sub_clip_id, in_frame, out_frame, step_s):
    """design/142 R6 (free): the stills the second look reads, from the shot as cut (its own in and out), not the logged piece's edges."""
    session = session_of(store, run)
    pk, row = _row(store, session, sub_clip_id)
    clip = session['package']['clips'][row['clip_id']]
    fps = Fraction(row['source_fps'])
    duration = float(clip.get('duration_s') or 0)
    a, z = float(Fraction(in_frame) / fps), float(Fraction(out_frame) / fps)
    if not (0 <= a < z <= duration + 0.04):
        fail(f'{sub_clip_id}: frames {in_frame}-{out_frame} are not inside the clip ({duration:.2f} s at {fps} fps)')
    rows = []
    with tempfile.TemporaryDirectory(prefix='vw2-stills-') as folder:
        original = Path(folder) / 'original.mp4'
        original.write_bytes(store.get(clip_key(run, clip)))
        for i, t in enumerate(still_times(a, z, float(step_s), fps), 1):
            out = Path(folder) / f'S{i}.png'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{t:.6f}', '-i', str(original), '-frames:v', '1', str(out)], check=True, capture_output=True, timeout=120)
            png = out.read_bytes()
            k = key(run, f"stills/{sub_clip_id.replace(':', '-')}-{in_frame}-{out_frame}/S{i}.png")
            store.put(k, png, 'image/png')
            rows.append({'frame_id': f'S{i}', 'at_s': t, 'key': k, 'sha256': hashlib.sha256(png).hexdigest()})
    return {'sub_clip_id': sub_clip_id, 'in_frame': in_frame, 'out_frame': out_frame, 'step_s': step_s, 'frames': rows}


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
        original.write_bytes(store.get(clip_key(run, clip)))
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
                                                                                   'rotation_deg': row.get('horizon_rotation_deg') or 0.0, 'hdr': str(clip.get('color_transfer') or '').lower() in ('arib-std-b67', 'smpte2084'),
                                                                                   **({'key': clip['key']} if clip.get('key') else {})},   # defect 60: a library clip's file is in its source film; without the key the render looked in this film's folder
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
        items = SL.review_items(doc, pk, _slides(store, session, doc, entry), lambda evs: _event_items(session, pk, evs, rows), timeline(run)['fps'])
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
    plan = {'kind': kind, 'items': items, 'timeline': timeline(run), 'narration_key': session['package']['narration_key'], 'narration': session['package'].get('narration'), 'version': version, 'digest': plan_digest,
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


def record_options(conn, store, user, run, quote, approved_by=None, film_needed=True):
    """The options output, recorded by the first slide answer (design/98 D2, D6): approved_by {'how': 'first_answer', 'slide': …}. The explicit
    approval beside it is retired (design/125 P14), refused."""
    if not approved_by:
        raise Problem(409, 'NOT_ALLOWED', 'The separate options approval is retired: answering the first slide approves the options.')
    session = session_of(store, run)
    doc, entry = current(store, session)
    _same_package(store, session, entry)
    _refresh(conn, store, run, session)
    if not film_needed:   # SK, 23 Nov 2026: the server's own record of a cut with no clip in it
        _film_less(run)
    review = _ready_film(session, 'review', entry['digest']) if film_needed else None
    files = [{'name': f"options-v{entry['version']}.json", **{k: entry['file'][k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True},
             *([{'name': 'review.mp4', 'key': review['key'], 'sha256': review['sha256'], 'bytes': review['bytes'], 'location': 'storage', 'receipt': True}] if review else []),
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
                                                    'review_film': {'sha256': review['sha256'], 'duration_s': review.get('duration_s')} if review else None, 'inspection_cost': inspection_cost,
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
RETIRED_ACTIONS = {'KEEP_WITH_EDIT': 'KEEP_WITH_EDIT is retired: use TRIM on the shot (--edit "start:seconds,end:seconds").',
                   'DROP': 'DROP is retired: answer the shot KEEP, REJECT or TRIM.'}
# SK, 23 Nov 2026 (VW-25): a trim is said in seconds. Older way kept until the next release: source frames.
TRIM_NEEDS = ('TRIM needs --edit "start:<seconds>,end:<seconds>": start later by, end earlier by; a minus value lengthens that end (start:0.5,end:0 starts half a second later). '
              'Older way, kept until the next release: "in:±frames,out:±frames" in source frames.')
FRAMES_EDIT = re.compile(r'^\s*(in|out):[+-]?\d+(\s*,\s*(in|out):[+-]?\d+)?\s*$')


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


def _slide_rows(sl, decisions, fps):
    """One row per scene, shot and alternative, with the answer so far (the page and the chat path show the same)."""
    rows = []
    for s in sl:
        lab = str(s['no'])
        d = decisions.get(lab)
        needs, why = needs_answer(s, sl, decisions)
        rows.append({'slide': lab, **{k: s.get(k) for k in ('type', 'title', 'scene', 'number', 'colour', 'hint', 'words', 'clip', 'b_roll', 'library', 'note', 'of', 'ai_only', 'intent', 'marker_reasons', 'flags')},
                     'fit': (d.get('swap') or {}).get('fit') if d and d.get('action') == 'SWAP' else s.get('fit'),   # VW-25 issue 3a: the mark of the piece now in use
                     'short': (d.get('swap') or {}).get('short') if d and d.get('action') == 'SWAP' else s.get('short'),   # VW-25 issue 3b: "Short shot, 1.4 s: one item of a list", of the piece now in use
                     'lines': list(s.get('lines') or []), 'seconds': round(s['frames'] / fps, 2), 'answerable': _answerable(s), 'needs_answer': needs, 'why': why,
                     'answer': ({k: d.get(k) for k in ('action', 'note', 'edit', 'edit_text', 'swap', 'by', 'at')} if d else None)})
    return rows


def _progress(rows):
    return {'answered': sum(1 for r in rows if r['needs_answer'] and r['answer']), 'of': sum(1 for r in rows if r['needs_answer']),
            'waiting': [r['slide'] for r in rows if r['needs_answer'] and not r['answer']]}


def slides_view(store, run):
    """Every row of the current version with the answer so far, and the labels still waiting (design/44 8.1)."""
    session = session_of(store, run)
    doc, entry = current(store, session)
    sl = _slides(store, session, doc, entry)
    rows = _slide_rows(sl, session.get('decisions') or {}, timeline(run)['fps'])
    return {'version': entry['version'], 'slides': rows, **_progress(rows), 'balance': _balance(store, run, session, doc, sl)}


def _balance(store, run, session, doc, sl):
    """SK, 23 Nov 2026 (VW-25): the scenes a trim left short or long, each with the shots that can take the time (review.balance).
    [] without a trim: a view with none reads nothing more."""
    decisions = session.get('decisions') or {}
    if not any(d.get('action') == 'TRIM' for d in decisions.values()):
        return []
    pk = _package(store, session)
    return RV.balance((doc or current(store, session)[0])['options'], decisions, sl, {r['sub_clip_id']: r for r in pk['sub_clips']},
                      {b['beat_id']: b['target_beat_frames'] for b in pk['beats']}, timeline(run)['fps'])


def _row_named(sl, slide_no):
    lab = slide_label(slide_no)
    return lab, next((x for x in sl if str(x['no']).upper() == lab), None)


def _shot_event(doc, s):
    return next(o for o in doc['options'] if o['option_number'] == s['option_number'])['events'][s['event_index']]


def _in_cut(sl, decisions, but=None):
    """The pieces in the cut as answered so far: every shot not rejected or swapped, a kept alternative of a rejected shot, a swapped-in piece.
    `but`: a row left out (its own piece is the one being replaced)."""
    out = set()
    for s in sl:
        d = decisions.get(str(s['no'])) or {}
        if str(s['no']) == but:
            continue
        if d.get('action') == 'SWAP':
            out.add(d['swap']['sub_clip_id'])
        elif s['type'] == 'shot' and d.get('action') != 'REJECT':
            out.add(s.get('sub_clip_id'))
        elif s['type'] == 'alternative' and d.get('action') == 'KEEP' and needs_answer(s, sl, decisions)[0]:
            out.add(s.get('sub_clip_id'))
    return out


def _swap_row(sl, lab):
    s = next((x for x in sl if str(x['no']).upper() == lab), None)
    if not s or not (s['type'] == 'shot' or (s['type'] == 'ai' and s.get('ai_only'))):
        fail(f'Other clips are for a footage shot or the AI shot of an all-AI scene; #{lab} is neither.')
    return s


def _placed_as(row, beat_id):
    """How a piece the operator puts on a shot is placed: a clip of the client's library, a direct match of the scene, else B-roll."""
    return 'library' if row.get('library') else 'direct' if P.rank_kind(row, beat_id) in ('exact', 'partly') else 'b_roll'


def _short_of(doc, s):
    """VW-25 issue 3b: the `short` of the shot a row stands for (None for an AI shot): a piece put on the shot under Other clips takes it."""
    return _shot_event(doc, s).get('short') if s['type'] == 'shot' else None


def others(store, run, slide_no):
    """SK, 23 Nov 2026 (VW-25): "Other clips" of one row, a footage shot or the AI shot of an all-AI scene ("Find footage"): the scene's allowed
    pieces in the server's one order (package.ranked: the assistant's files, the ledger and this list read it), each with whether it can be
    used on this row and, when not, why. A read; the page and `vw master others` call it."""
    session = session_of(store, run)
    doc, entry = current(store, session)
    sl = _slides(store, session, doc, entry)
    lab = slide_label(slide_no)
    s = _swap_row(sl, lab)
    pk = _package(store, session)
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    bid = next(o for o in doc['options'] if o['option_number'] == s['option_number'])['beat_id']
    decisions = session.get('decisions') or {}
    used, fps, clips = _in_cut(sl, decisions, lab), timeline(run)['fps'], session['package'].get('clips') or {}
    chosen = ((decisions.get(lab) or {}).get('swap') or {}).get('sub_clip_id')
    short = _short_of(doc, s)
    pieces = []
    for x in P.ranked(pk['sub_clips'], next(b for b in pk['beats'] if b['beat_id'] == bid), used):
        if x['sub_clip_id'] == s.get('sub_clip_id'):   # the row's own piece: Keep brings it back
            continue
        row = rows[x['sub_clip_id']]
        fit = RV.fit_piece(row, s['frames'], fps, partial=s['type'] == 'ai', short=short, match=_placed_as(row, bid))
        a, z = (row['in_frame'], row['out_frame']) if isinstance(fit, str) else fit[:2]
        k, src = clip_key(run, clips.get(row['clip_id']) or {'name': row.get('clip_name')}), Fraction(str(row['source_fps']))
        in_cut = x['sub_clip_id'] in used
        pieces.append({**x, 'clip': row.get('clip_name'), 'what': row.get('what'), 'chapter': row.get('process_stage'), 'grade': row.get('grade'), 'flags': list(row.get('risk_flags') or []),
                       'library': bool(row.get('library')), 'chosen': x['sub_clip_id'] == chosen, 'in_cut': in_cut, 'can': not in_cut and not isinstance(fit, str),
                       'why': 'already in the cut' if in_cut else fit if isinstance(fit, str) else '',
                       # a library clip's file is in another film's folder, which this film's page does not serve: no preview
                       'media': {'key': k if k.startswith(f"{run['id']}/") else None, 'in_s': round(float(a / src), 2), 'out_s': round(float(z / src), 2)}})
    return {'slide': lab, 'title': s['title'], 'seconds': round(s['frames'] / fps, 2), 'pieces': pieces,
            'empty': '' if pieces else 'No clip fits this scene. Keep AI.' if s['type'] == 'ai' else 'No other clip fits this scene.'}


def trim_room(store, run, slide_no):
    """What the trim form says before the operator types: the shot's length and how much it can lose and gain, in seconds. A read."""
    session = session_of(store, run)
    doc, entry = current(store, session)
    lab, s = _row_named(_slides(store, session, doc, entry), slide_no)
    if not s or s['type'] != 'shot':
        fail(f'A trim is for a footage shot; #{lab} is not one.')
    ev = _shot_event(doc, s)
    return {'slide': lab, 'text': RV.room_text(ev['source_in_frame'], ev['source_out_frame'], _row(store, session, ev['sub_clip_id'])[1],
                                               ev.get('short'), bool(ev.get('hold_last_frame')), ev.get('match'))}


def _swap(run, session, pk, doc, sl, s, sub_clip_id):
    """SWAP: the piece the operator chose under Other clips, fitted to the row's length around its main action (review.fit_piece); refused
    with the reason when it cannot be used there. Returns what the master places."""
    if not sub_clip_id:
        fail('SWAP needs the piece: --sub <sub-clip id>, from `vw master others --slide <label>`.')
    row = next((r for r in pk['sub_clips'] if r['sub_clip_id'] == sub_clip_id), None)
    if not row:
        fail(f'{sub_clip_id} is not a piece of this film.')
    if sub_clip_id in _in_cut(sl, session['decisions'], str(s['no'])):
        fail(f'{sub_clip_id} is already in the cut.')
    if not str(row.get('eligibility')).startswith('ELIGIBLE'):
        fail(f"{sub_clip_id} is not allowed in the film ({row.get('eligibility')}).")
    o = next(o for o in doc['options'] if o['option_number'] == s['option_number'])
    match, short, fps = _placed_as(row, o['beat_id']), _short_of(doc, s), timeline(run)['fps']
    fit = RV.fit_piece(row, s['frames'], fps, partial=s['type'] == 'ai', short=short, match=match)
    if isinstance(fit, str):
        fail(f"{sub_clip_id} cannot be used on {s['title']}: {fit}.")
    line = RV.short_text(fit[0], fit[1], row, short, False, fit[2] / fps)   # VW-25 issue 3b: the card's line follows the piece now on the shot
    # SK, 25 Nov 2026 (VW-25 issue 3a): the review page's part-match label follows the piece now on the shot (slides.fit, as for a proposed shot)
    mark = SL.fit(row, o, next(b for b in pk['beats'] if b['beat_id'] == o['beat_id']), s['event_index'] + 1, s['at_frame'], s['at_frame'] + fit[2]) if match == 'direct' else None
    return {'sub_clip_id': sub_clip_id, 'source_in_frame': fit[0], 'source_out_frame': fit[1], 'timeline_frames': fit[2], 'crop': 'solver' if row['eligibility'] == 'ELIGIBLE_WITH_CROP' else 'full',
            'match': match, 'clip': row.get('clip_name'), **({'fit': mark} if mark else {}), **({'short': line} if line else {})}


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
            _CUES[k] = slide_cues(plan, timeline(run)['fps']) if plan.get('digest') == entry['digest'] else {}
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
    rows = _slide_rows(sl, session.get('decisions') or {}, timeline(run)['fps'])
    r = session['renders'].get('review') or {}
    film, cues = None, {}
    is_current = bool(r) and r.get('digest') == entry['digest']
    if is_current and r.get('status') == 'ready' and (r.get('result') or {}).get('key'):
        film = {'key': r['result']['key'], 'duration_s': r['result'].get('duration_s'), 'sha256': r['result'].get('sha256')}
        cues = _cues_for(store, run, entry)
    accepted = session.get('accepted') or {}
    return {'state': 'prepared', 'version': entry['version'], 'digest': entry['digest'], 'slides': rows, **_progress(rows), 'film': film, 'cues': cues,
            'render': ({'status': r.get('status'), 'error': r.get('error'), 'current': is_current} if r else None),
            'accepted': bool(accepted) and accepted.get('digest') == entry['digest'], 'approved_by': accepted.get('approved_by'), 'master_built': bool(session.get('master')),
            'second_look': entry.get('second_look'), 'balance': _balance(store, run, session, None, sl)}   # design/129 P4


def master_state(master, render, exists):
    """design/185: what the master page shows, from the built master, its render record and a storage check. View only."""
    if not master:
        return {'state': 'none'}
    out = {'version': master.get('version')}
    if not render or render.get('digest') != master.get('digest'):
        return {**out, 'state': 'not_rendered'}
    if render.get('status') in ('queued', 'running'):
        return {**out, 'state': 'rendering'}
    result = render.get('result') or {}
    if render.get('status') != 'ready' or not result.get('key'):
        return {**out, 'state': 'failed', 'error': render.get('error') or 'see the render record'}
    if not exists(result['key']):
        return {**out, 'state': 'missing'}
    return {**out, 'state': 'ready', 'key': result['key'], 'duration_s': result.get('duration_s'), 'mix': (result.get('record') or {}).get('mix')}


def master_view(conn, store, run):
    """design/185: a read for the master page; no write (a revise or a new build drops the master, so the page then says none)."""
    try:
        session = session_of(store, run)
    except Problem:
        return {'state': 'none'}
    _refresh(conn, store, run, session)
    return {**master_state(session.get('master'), (session.get('renders') or {}).get('master'), store.exists), 'recorded': bool((session.get('recorded') or {}).get('master'))}


def _refuse_answer(s, sl, decisions, lab, action, edit):
    """design/127: the answer each row takes, refused by name otherwise."""
    if action in RETIRED_ACTIONS:
        fail(RETIRED_ACTIONS[action])
    if action not in ('KEEP', 'REJECT', 'TRIM', 'SWAP'):
        fail('action must be KEEP, REJECT, TRIM or SWAP')
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
        fail(TRIM_NEEDS)
    if action == 'SWAP':
        _swap_row(sl, lab)
    if s['type'] == 'alternative':
        needs, why = needs_answer(s, sl, decisions)
        if not needs:
            fail(why + ': its alternatives open when it is rejected.' if why.startswith('answer') else why + '.')


def decide(conn, store, user, run, slide_no, action, note, edit, sub_clip_id=None):
    """design/127: the operator answers by row: a footage shot KEEP, REJECT or TRIM; the AI shot of an all-AI scene KEEP (Keep AI) or REJECT
    (Find footage); an alternative KEEP or REJECT once its shot is rejected. SK, 23 Nov 2026 (VW-25): SWAP puts another piece on a footage shot or
    on an all-AI scene (`sub_clip_id`, from `others`); a TRIM is in seconds and is checked here, when it is recorded, not at the master. design/98: the first answer approves the options (the options output
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
    more = {}
    if action == 'SWAP':
        more = {'swap': _swap(run, session, _package(store, session), doc, sl, s, sub_clip_id)}
    if action == 'TRIM':
        ev = _shot_event(doc, s)
        row = _row(store, session, ev['sub_clip_id'])[1]
        edit = RV.seconds_edit(edit, row) or str(edit)
        if not FRAMES_EDIT.match(edit):
            fail(TRIM_NEEDS)
        _trim(deepcopy(ev), edit, row, timeline(run)['fps'], s['title'])
        more = {'edit': edit, 'edit_text': RV.edit_text(edit, row)}
    approved_now = not session.get('accepted')
    if approved_now:   # design/98 D2: the first answer approves these options, with what was answered
        record_options(conn, store, user, run, f'Approved by answering the review slides: first answer #{lab} {action}' + (f' — {note.strip()}' if str(note or '').strip() else ''),
                       {'how': 'first_answer', 'slide': lab})
        session = session_of(store, run)
    if action == 'REJECT' and s.get('library') and s.get('sub_clip_id'):   # design/147 L4 (E9): a rejected library proposal is not offered again on this film
        session['library_rejected'] = sorted(set(session.get('library_rejected') or []) | {s['sub_clip_id']})
    session['decisions'][lab] = {'action': action, 'type': s['type'], **more,
                                 'note': note or '', 'by': user['id'], 'at': datetime.now(timezone.utc).isoformat()}
    session['master'] = None
    save_session(store, run, session)
    progress = _progress(_slide_rows(sl, session['decisions'], timeline(run)['fps']))
    return {'slide': lab, 'type': s['type'], 'action': action, 'decided': progress['answered'], 'of': progress['of'], **more,
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


def _trim(ev, edit, row, tl_fps, title):
    """design/127: TRIM on one footage shot: its in and out moved by source frames, inside its usable window, its action peak and its hold.
    SK, 25 Nov 2026 (VW-25 issue 3b): the limits are the one rule in review.limits, so a shot marked `short` may go down to 1.0 s, and a
    normal shot has the two exceptions of the proposal's check (a still frame held at the end, a cut that ends where a reported camera move
    starts). Older way retired: the rule written out here, without those two exceptions."""
    e = RV.parse_edit(edit)
    short, held, match = ev.get('short'), bool(ev.get('hold_last_frame')), ev.get('match')
    room = '. ' + RV.room_text(ev['source_in_frame'], ev['source_out_frame'], row, short, held, match)   # SK, 23 Nov 2026: a refused trim says what the shot can lose and gain
    a, z = ev['source_in_frame'] + e['in'], ev['source_out_frame'] + e['out']
    if not (row['in_frame'] <= a < z <= row['out_frame']):
        fail(f"the trim leaves {title} outside its usable window {row['in_frame']}-{row['out_frame']}" + room)
    how = RV.judge(a, z, row, short, held, match)
    peak, action = row.get('action_peak'), how['action']
    if how['why']:
        fail(f"the trim cannot be made on {title}: {how['why']}" + room)
    if action and not (a <= action[0] and action[1] <= z):
        fail(f"the trim drops the action peak {peak['in_frame']}-{peak['out_frame']} of {title}" + room)
    if z - a < how['least']:
        fail((f"the trim makes {title} shorter than {RV.SHORT_S:.1f} s, the least for a short shot" if how['short'] else f"the trim makes {title} shorter than its hold {row['min_hold_s']} s") + room)
    ev['source_in_frame'], ev['source_out_frame'] = a, z
    ev['timeline_frames'] = int(round((z - a) * Fraction(str(tl_fps)) / Fraction(row['source_fps'])))
    ev['edited'] = edit
    return ev


SWAP_KEYS = ('sub_clip_id', 'source_in_frame', 'source_out_frame', 'timeline_frames', 'crop', 'match')   # what a swapped-in piece gives the master


def _shot_name(s, ev):
    """SK, 23 Nov 2026 (Phase 4b): what the editor is told a cut is: its row on the review page, its name, the words under it, how it matches them."""
    return {'slide': s['no'], 'title': s['title'], 'words': s.get('words') or '', 'match': ev.get('match')}


def _overview(card):
    """design/126 MA1: what a clip shows, from its card's OVERVIEW line (some cards number their lines), else its descriptive name."""
    line = next((str(l) for l in card.get('lines') or [] if re.match(r'^\d*\s*OVERVIEW:', str(l))), '')
    return line.split('OVERVIEW:', 1)[1].strip() if line else str(card.get('descriptive_name') or '')


NOTE_NOT_USED = {'KEEP': 'the shot is kept', 'TRIM': 'the shot is trimmed', 'SWAP': "the shot is replaced by the operator's clip"}


def note_outcomes(sl, decisions):
    """SK, 25 Nov 2026 (VW-25 issue 5): what the master build did with every note on an answer, in film order, for the assistant to tell the
    operator: the row's label and name, the answer, the note (400 characters at most here; whole in the record) and the outcome. Only the note
    of a rejected shot that becomes an AI stretch is passed on (inside that stretch's request to the visuals stage); every other note is
    'not used', with why. A note of spaces is no note. A report only: it refuses nothing. Older way retired: a note that was not used was
    dropped without a word."""
    out = []
    for s in sl:
        d = decisions.get(str(s['no'])) or {}
        note = str(d.get('note') or '').strip()
        if not note:
            continue
        if s['type'] != 'shot':
            did = f"not used: a note on {'an alternative' if s['type'] == 'alternative' else 'an AI shot'} is not passed on"
        elif d.get('action') != 'REJECT':
            did = 'not used: ' + NOTE_NOT_USED.get(d.get('action'), 'the shot is kept')
        elif any(x['type'] == 'alternative' and x.get('of') == s['no'] and _action(decisions, x) == 'KEEP' for x in sl):
            did = "not used: the kept alternative took the shot's place"
        else:
            did = 'passed to the visuals stage as the request for this stretch'
        out.append({'slide': str(s['no']), 'title': s['title'], 'answer': d.get('action'), 'note': note[:400], 'outcome': did})
    return out


def build_master(conn, store, user, run):
    """design/127: per shot: KEEP the shot, TRIM it, or REJECT it for its kept alternative, else an AI stretch with its words; adjacent AI
    stretches merge; an all-AI scene answered Find footage goes back to the assistant."""
    session = session_of(store, run)
    if not session.get('accepted'):
        raise Problem(409, 'NOT_ALLOWED', 'Record the options stage first.')
    doc, entry = current(store, session)
    pk = _package(store, session)
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    seen = {c.get('clip_id'): _overview(c) for c in pk.get('cards') or []}
    beats = pk['beats']
    decisions = session['decisions']
    sl = _slides(store, session, doc, entry)
    left = set(missing_answers(sl, decisions))
    missing = [f"{s['title']} (#{s['no']})" for s in sl if str(s['no']) in left]
    if missing:   # SK, 25 Nov 2026 (VW-25 issue 4): each missing shot by its name on the page, five at most, then the page (its path: the tool holds the full link). Older way retired: the bare "#2.1"
        fail(f"Every shot needs an answer; missing: {', '.join(missing[:5])}" + (f' and {len(missing) - 5} more' if len(missing) > 5 else '') + f". Review page: /runs/{run['code']}/review")
    row_of = {(s['option_number'], s['type'], s.get('event_index'), s.get('alt_index')): s for s in sl}
    fps = timeline(run)['fps']
    kept, turned = {}, {}
    for o in deepcopy(doc['options']):
        n_scene = row_of[(o['option_number'], 'scene', None, None)]['number']
        events = []
        for i, ev in enumerate(o['events']):
            if ev.get('blank'):
                s = row_of[(o['option_number'], 'ai', i, None)]
                if s.get('ai_only') and _action(decisions, s) == 'SWAP':   # SK, 23 Nov 2026: Find footage chose a piece; AI keeps what the piece does not fill
                    sw = decisions[s['no']]['swap']
                    events.append({**{k: sw[k] for k in SWAP_KEYS}, 'swapped_from': 'AI', 'shot': _shot_name(s, sw)})
                    if ev['timeline_frames'] > sw['timeline_frames']:
                        events.append({**ev, 'timeline_frames': ev['timeline_frames'] - sw['timeline_frames']})
                    continue
                if s.get('ai_only') and _action(decisions, s) == 'REJECT':
                    fail(f"Scene {n_scene}: the operator asked to find footage (Find footage on {s['no']}): they pick a piece under Other clips "
                         f"(`vw master others --slide {s['no']}`), or answer Keep AI, or the scene is proposed again with footage (`vw options propose`).")
                events.append(ev)
                continue
            s = row_of[(o['option_number'], 'shot', i, None)]
            act = _action(decisions, s)
            if act == 'TRIM':
                ev = _trim(ev, decisions[s['no']]['edit'], rows[ev['sub_clip_id']], fps, s['title'])
            if act == 'SWAP':   # SK, 23 Nov 2026: the operator's own choice under Other clips takes the shot's place and its length
                sw = decisions[s['no']]['swap']
                turned[(o['option_number'], i)] = f"the operator chose {sw['sub_clip_id']} instead"
                ev = {**{k: sw[k] for k in SWAP_KEYS}, 'swapped_from': ev['sub_clip_id']}
            if act == 'REJECT':
                turned[(o['option_number'], i)] = str((decisions.get(str(s['no'])) or {}).get('note') or '').strip()
                alt = next((row_of[(o['option_number'], 'alternative', i, m)] for m in range(len(ev.get('alternatives') or []))
                            if _action(decisions, row_of[(o['option_number'], 'alternative', i, m)]) == 'KEEP'), None)
                if alt:
                    ev = {**ev['alternatives'][alt['alt_index']], 'timeline_frames': ev['timeline_frames'], 'from_alternative': alt['no']}
                else:
                    note = str((decisions.get(str(s['no'])) or {}).get('note') or '').strip()   # design/126 MA1: what was turned down and why; the words stay in the narration part
                    ev = {'blank': True, 'timeline_frames': ev['timeline_frames'],
                          'intent': f"in place of rejected {s['title']} (it showed: {seen.get(rows[ev['sub_clip_id']].get('clip_id'), '')}" + (f"; the operator: {note}" if note else '') + ')',
                          'rejected': s['no'], 'title': s['title']}
            elif (ev.get('note') or {}).get('kind') == 'reuse':
                ev['reuse_approved'] = True
            events.append(ev if ev.get('blank') else {**ev, 'shot': _shot_name(s, ev)})
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
                           **({'from_alternative': ev['from_alternative']} if ev.get('from_alternative') else {}),
                           **({'swapped_from': ev['swapped_from']} if ev.get('swapped_from') else {}), 'shot': ev['shot']})
            cursor += n
    plan = {'contract': CONTRACT_MASTER, 'run_id': str(run['id']), 'options_version': entry['version'], 'options_digest': entry['digest'], 'timeline': timeline(run), 'events': events,
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
    LG.write(conn, run, entry['version'], [r for r in LG.rows(pk, doc, turned) if r['decided_by'] == 'operator'])   # the operator's Reject, with the note
    return {'version': version, 'events': session['master']['events'], 'gaps': session['master']['gaps'], 'flags': result['flags'], 'duration_frames': cursor,
            'notes': note_outcomes(sl, decisions), 'next': '`vw master render`, fetch, let the operator watch, then `vw master record --quote`'}


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


def _first_cut_output(conn, user, run, master_id, film, summary, quote, movie=True):   # movie False: a film with no footage; its file is the master's plan
    """The approved master film as the first cut: hash-bound to the film, the master's gaps and timeline (design/17 A50)."""
    files = [{'name': 'first-cut.mp4' if movie else film['name'], 'key': film['key'], 'sha256': film['sha256'], 'bytes': film['bytes'], 'location': 'storage', 'receipt': True}]
    return core.output(conn, user, run, {'stage': 'first_cut', 'files': files, 'accepted_quote': quote,
                                         'summary': {'movie_sha256': film['sha256'] if movie else None, 'master_output': str(master_id), 'plan_digest': summary['plan_digest'], 'fps': summary['fps'],
                                                     'resolution': summary['resolution'], 'duration_frames': summary['duration_frames'], 'gaps': summary['gaps']}})


def record_master(conn, store, user, run, quote, film_needed=True):
    """design/44 8.4: one approval records the master and the first cut; the quote must say watched and listened. SK, 23 Nov 2026: the server's own
    record of a cut with no clip in it (`film_needed` False, a film with no camera footage only) has no film to watch: its words are the scenes'."""
    if not film_needed:
        _film_less(run)
    session = session_of(store, run)
    m = session.get('master')
    if not m:
        raise Problem(409, 'NOT_ALLOWED', 'Build the master first.')
    q = (quote or '').lower()
    if film_needed and ('watch' not in q or 'listen' not in q):
        fail(FIRST_CUT_WORDS)
    _refresh(conn, store, run, session)
    film = _ready_film(session, 'master', m['digest']) if film_needed else None
    files = [{'name': f"master-v{m['version']}.json", **{k: m['file'][k] for k in ('key', 'sha256', 'bytes')}, 'location': 'storage', 'receipt': True},
             *([{'name': 'master.mp4', 'key': film['key'], 'sha256': film['sha256'], 'bytes': film['bytes'], 'location': 'storage', 'receipt': True}] if film else [])]
    for f in files:
        jobs.record_file(conn, run['id'], 'master', f['key'], f['name'], f['sha256'], f['bytes'], 'application/json' if f['name'].endswith('.json') else 'video/mp4')
    # learned rules (design/43 7.5): only the rules the operator confirmed; rejection notes stay on this run's decisions
    plan = m['plan']
    added = 0
    for r in plan['extra_rules']:
        conn.execute("insert into vw2_client_rules(client_id, rule, source_run) values (%s,%s,%s)", (run.get('client_id') or '', r['rule'], run['code']))
        added += 1
    summary = {'version': m['version'], 'plan_digest': m['digest'], 'fps': str(timeline(run)['fps']), 'resolution': [timeline(run)['width'], timeline(run)['height']], 'duration_frames': plan['duration_frames'],
               'gaps': plan['gaps'], 'units': {'visuals': [g['shot_id'] for g in plan['gaps']]}, 'events': m['events'], 'learned_rules_added': added,
               'film': {'sha256': film['sha256'], 'duration_s': film.get('duration_s'), 'mix': (film.get('record') or {}).get('mix')} if film else None,
               **({} if film else {'written_by': 'server'})}
    out = core.output(conn, user, run, {'stage': 'master', 'files': files, 'accepted_quote': quote, 'summary': summary})
    first = _first_cut_output(conn, user, run, out['id'], files[-1], summary, quote, movie=bool(film))
    session['recorded']['master'] = str(out['id'])
    session['recorded']['first_cut'] = str(first['id'])
    save_session(store, run, session)
    return {'output': str(out['id']), 'first_cut_output': str(first['id']), 'version': m['version'], 'gaps': [g['shot_id'] for g in summary['gaps']], 'learned_rules_added': added,
            'next': 'visuals for each gap' if summary['gaps'] else 'assembly'}


def record_first_cut(conn, store, user, run, outputs, quote):
    """Retired (design/44 8.4, design/125): the separate first-cut record is refused; `record_master` records both."""
    raise Problem(409, 'NOT_ALLOWED', 'The separate first-cut record is retired: the first cut is recorded with the master (`vw master record`).')
