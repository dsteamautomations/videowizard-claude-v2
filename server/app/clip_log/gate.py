"""The gate for clip-log-v1: identity, strict validation with per-sub-clip salvage, timecode consistency, card length, then the solver.
Gate, not repair: nothing is resubmitted."""
import json
import math
import re
from copy import deepcopy
from fractions import Fraction

from . import CONTRACT, schema as S, solver

TC_RE = re.compile(r'^(\d{2}):(\d{2}):(\d{2})[:;](\d{2})$')


def tc_to_frame(tc, fps):
    m = TC_RE.match(tc or '')
    if not m:
        return None
    h, mi, s, f = (int(x) for x in m.groups())
    return round((h * 3600 + mi * 60 + s) * fps) + f


def _finite(v):
    return isinstance(v, (int, float)) and math.isfinite(v)


def timecode_gaps(sub, fps, duration_frames):
    """Gaps (not failures) when HH:MM:SS:FF, seconds and frames disagree, or frames leave the clip. Returns (gaps, usable_window)."""
    gaps = []
    w = sub.get('max_usable_window') or {}
    for key in ('in', 'out'):
        tc, s, fr = w.get(f'{key}_tc'), w.get(f'{key}_s'), w.get(f'{key}_frame')
        tf = tc_to_frame(tc, fps)
        if tf is None:
            gaps.append(f"{sub.get('sub_clip_id')}: {key}_tc {tc!r} is not HH:MM:SS:FF")
            continue
        if _finite(s) and abs(round(s * fps) - tf) > 1:
            gaps.append(f"{sub.get('sub_clip_id')}: {key}_tc {tc} and {key}_s {s} disagree at {fps:g} fps")
        if isinstance(fr, int) and abs(fr - tf) > 1:
            gaps.append(f"{sub.get('sub_clip_id')}: {key}_frame {fr} and {key}_tc {tc} disagree")
    usable = isinstance(w.get('in_frame'), int) and isinstance(w.get('out_frame'), int) and 0 <= w['in_frame'] < w['out_frame'] < max(duration_frames, 1) + 1
    if not usable:
        gaps.append(f"{sub.get('sub_clip_id')}: window frames must satisfy 0 <= in_frame < out_frame < duration_frames ({duration_frames})")
    for ev in (sub.get('pacing_and_flow') or {}).get('accent_events', []) + (sub.get('pacing_and_flow') or {}).get('natural_cut_points', []):
        tf = tc_to_frame(ev.get('tc'), fps)
        if tf is not None and isinstance(ev.get('frame'), int) and abs(ev['frame'] - tf) > 1:
            gaps.append(f"{sub.get('sub_clip_id')}: event {ev.get('tc')} frame {ev['frame']} disagrees")
    return gaps, usable


def review(raw, request):
    """request: the frozen request (identity, schema, clip, policy, timeline, fps, duration_frames). Returns the reviewed document."""
    out = {'contract_version': CONTRACT, 'status': 'retained', 'raw': raw, 'log': None, 'gaps': [], 'excluded_sub_clips': [], 'identity_errors': []}
    try:
        def reject(_):
            raise ValueError('Non-finite JSON')

        def finite(value):
            number = float(value)
            if not math.isfinite(number):
                raise ValueError('Non-finite JSON')
            return number
        body = json.loads(raw, parse_constant=reject, parse_float=finite)
        if not isinstance(body, dict):
            raise ValueError('not an object')
    except (ValueError, TypeError):
        out.update(status='retained_unstructured', gaps=['The provider answer is not structured JSON. Preserve it for review; do not automatically regenerate.'])
        return out
    clip = request['clip']
    expected_id, expected_name = request['identity']['clip_tag'], clip['name']
    if body.get('clip_id') != expected_id:
        out['identity_errors'].append(f"clip_id {body.get('clip_id')!r} is not {expected_id!r}")
    if body.get('filename') != expected_name:
        out['identity_errors'].append(f"filename {body.get('filename')!r} is not {expected_name!r}")
    if not str(body.get('descriptive_name') or '').strip():
        out['identity_errors'].append('descriptive_name missing')
    if out['identity_errors']:
        out['status'] = 'identity_mismatch'
        return out
    strict = request['schema']
    fps = float(Fraction(str(request['fps'])))
    duration_frames = int(request['duration_frames'])
    # per-sub-clip salvage: an invalid sub-clip is excluded with its errors, the rest stay
    sub_schema = S.sub_clip_schema()
    kept = []
    for i, sub in enumerate(body.get('sub_clips') or []):
        errs = S.errors(sub, sub_schema) if isinstance(sub, dict) else ['not an object']
        sid = sub.get('sub_clip_id') if isinstance(sub, dict) else f'#{i}'
        if errs:
            out['excluded_sub_clips'].append({'sub_clip_id': sid, 'index': i, 'errors': errs[:8]})
            continue
        gaps, usable = timecode_gaps(sub, fps, duration_frames)
        out['gaps'].extend(gaps)
        if not usable:
            out['excluded_sub_clips'].append({'sub_clip_id': sid, 'index': i, 'errors': ['window frames outside the clip']})
            continue
        kept.append(sub)
    log = {**body, 'sub_clips': kept}
    top_errors = S.errors({**log, 'sub_clips': []}, {**strict, 'properties': {**strict['properties'], 'sub_clips': {'type': 'array'}}})
    lines = body.get('summary_card_lines')
    card_bad = [e for e in top_errors if e.startswith('summary_card_lines')]
    top_errors = [e for e in top_errors if not e.startswith('summary_card_lines')]
    if top_errors:
        out['gaps'].extend('clip level: ' + e for e in top_errors[:10])
    if card_bad or not isinstance(lines, list) or len(lines) != 10:
        out['gaps'].append(f"summary_card_lines has {len(lines) if isinstance(lines, list) else 'no'} lines, not 10")
    if request.get('audio_removed'):
        for sub in kept:
            if (sub['people_and_speaker_analysis'] or {}).get('speech_translation_block'):
                out['gaps'].append(f"{sub['sub_clip_id']}: speech reported although audio was removed for analysis")
    ids = [s['sub_clip_id'] for s in kept]
    if len(ids) != len(set(ids)):
        out['gaps'].append('duplicate sub_clip_id values')
    if not body.get('unavailable_or_uncertain') and any((s['people_and_speaker_analysis'] or {}).get('speech_translation_block') or (s['people_and_speaker_analysis'] or {}).get('speaker_crop_module') for s in kept):
        out['gaps'].append('model reported no uncertainty although nullable blocks are filled')
    solver.solve(log, request['policy'], clip, request['timeline'])
    for sub in kept:
        for n in sub['stage15'].get('notes') or []:
            out['gaps'].append(f"{sub['sub_clip_id']}: {n}")
    out['log'] = log
    return out


def evidence_document(reviewed, request, clip):
    log = reviewed['log']
    return {'contract_version': CONTRACT, 'identity': request['identity'], 'clip': clip, 'log': log, 'gaps': reviewed['gaps'],
            'excluded_sub_clips': reviewed['excluded_sub_clips'], 'summary_card': log.get('summary_card_lines') or [],
            'descriptive_name': log.get('descriptive_name'), 'solver_version': 1}


def summary_of(reviewed, clip):
    log = reviewed.get('log') or {}
    subs = log.get('sub_clips') or []
    by_elig, by_grade = {}, {}
    for s in subs:
        e = s['stage15']['visual_eligibility']
        by_elig[e] = by_elig.get(e, 0) + 1
        g = s['usability_grade']
        by_grade[g] = by_grade.get(g, 0) + 1
    return {'contract_version': CONTRACT, 'status': reviewed['status'], 'clip': {k: clip.get(k) for k in ('id', 'name', 'duration_s')},
            'descriptive_name': log.get('descriptive_name'), 'sub_clips': len(subs), 'by_eligibility': by_elig, 'by_grade': by_grade,
            'speech_present': any((s['people_and_speaker_analysis'] or {}).get('speech_translation_block') for s in subs),
            'risk_flags': sum(len(s.get('risk_flags') or []) for s in subs), 'excluded_sub_clips': len(reviewed.get('excluded_sub_clips') or []),
            'gaps': len(reviewed.get('gaps') or []), 'identity_errors': reviewed.get('identity_errors') or [],
            'summary_card': log.get('summary_card_lines') or []}
