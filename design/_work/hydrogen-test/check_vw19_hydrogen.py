"""The 14 checks of design/_work/hydrogen-test-list.md on the answers in out-vw19-hydrogen/ (13 Nov 2026).
Reads the answers, the application's code (import only: the server's own arrival check and allowed-or-not rule) and VW-19's run folder (read only).
Writes out-vw19-hydrogen/checks.json and checks.md. Sends nothing, costs nothing.  Usage: python -X utf8 check_vw19_hydrogen.py"""
import json
import re
import statistics
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

import run_vw19_hydrogen as R
from app import analysis
from app.stage2 import package as P

OUT = R.OUT
EMPTY = (None, '', [], {})
run, procedure, brief, script, clips = R.inputs()
BY_NAME = {c['name']: c for c in clips}
POL = {**R.POLICY, 'collection': [{'id': c['id'], 'sha256': c['sha256']} for c in clips]}
T4 = ['C0032_02881492.mp4', 'C0114_02782204.mp4', 'C0113_02781556.mp4', 'C0134_02797372.mp4']


def answer(name, mode):
    p = OUT / f'{name}.{mode}.response.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else None


def usage_row(a):
    u = (a['metadata'].get('usage') or {})
    video = sum(d.get('tokenCount') or 0 for d in (u.get('promptTokensDetails') or []) + (u.get('toolUsePromptTokensDetails') or []) if d.get('modality') == 'VIDEO')
    tin = (u.get('promptTokenCount') or 0) + (u.get('toolUsePromptTokenCount') or 0)
    tout = (u.get('candidatesTokenCount') or 0) + (u.get('thoughtsTokenCount') or 0)
    return {'in': tin, 'video_in': video, 'out': u.get('candidatesTokenCount') or 0, 'thinking': u.get('thoughtsTokenCount') or 0, 'usd': R.cost_of(u), 'seconds': a.get('seconds'),
            'looks': a['metadata'].get('media_processing_calls') or 0, 'finish': a['metadata'].get('finish_reason')}


def leaves(v, path=''):
    """Every field of an answer as (path, value). An object counts as one field (filled or empty) and its inner fields are walked too; a list of
    objects likewise, under the same name whether it is empty or not; a list of plain values is one field."""
    if isinstance(v, dict):
        if path:
            yield path, v
        for k, x in v.items():
            yield from leaves(x, f'{path}.{k}' if path else k)
    elif isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
        yield path, v
        for x in v:
            for k, y in x.items():
                yield from leaves(y, f'{path}[].{k}')
    else:
        yield path, v


def reviewed_of(name, mode):
    a = answer(name, mode)
    if not a:
        return None, None, None
    req = analysis.build_request(run, procedure, brief, script, BY_NAME[name], POL)
    return a, req, analysis.review_response(a['raw'], req)


def main():
    res = {}
    # ---- which way each clip is watched in production, and the answers there are ----
    auto = {c['name']: ('AGENTIC' if c['duration_s'] > 15 else 'STATIC') for c in clips}
    led = json.loads((OUT / 'ledger.json').read_text(encoding='utf-8'))
    rows = {}
    for name, mode in auto.items():
        a, req, rv = reviewed_of(name, mode)
        if a:
            rows[name] = {'mode': mode, 'a': a, 'req': req, 'rv': rv, 'clip': BY_NAME[name]}
    errors = [r for r in led['requests'] if r.get('error')]

    # T1
    res['T1'] = {'clips': len(clips), 'answered': len(rows), 'by_way': dict(Counter(r['mode'] for r in rows.values())),
                 'missing': sorted(n for n in auto if n not in rows), 'failed_requests': [{k: e.get(k) for k in ('clip', 'mode', 'error', 'http_status', 'provider_error', 'seconds')} for e in errors],
                 'plain_fallback': sorted(n for n, r in rows.items() if r['a'].get('plain_fallback')), 'finish_reasons': dict(Counter(r['a']['metadata'].get('finish_reason') for r in rows.values()))}

    # T2, T3
    status, kept, dropped, notes, elig, drop_errors = Counter(), 0, 0, Counter(), Counter(), Counter()
    pieces = []   # (clip name, clip log, piece)
    for name, r in rows.items():
        rv = r['rv']
        status[rv['status']] += 1
        dropped += len(rv['excluded_sub_clips'])
        for x in rv['excluded_sub_clips']:
            for e in x['errors'][:3]:
                drop_errors[re.sub(r'\d+', 'N', str(e))[:110]] += 1
        for g in rv['gaps']:
            notes[re.sub(r'SUB_[A-Z0-9_]+', 'SUB', re.sub(r'\d+(\.\d+)?', 'N', str(g)))[:110]] += 1
        for sub in (rv.get('log') or {}).get('sub_clips') or []:
            kept += 1
            elig[sub['stage15']['visual_eligibility']] += 1
            pieces.append((name, rv['log'], sub))
    res['T2'] = {'answer_status': dict(status), 'pieces_kept': kept, 'pieces_thrown_out': dropped, 'thrown_out_reasons': drop_errors.most_common(10), 'notes_total': sum(notes.values()), 'notes': notes.most_common(15)}
    res['T3'] = {'allowed_or_not': dict(elig), 'speaker_box_notes': sum(n for k, n in notes.items() if 'head box' in k or 'crop box' in k)}

    # T4: the four short clips, both ways
    t4 = []
    for name in T4:
        row = {'clip': name, 'seconds_long': BY_NAME[name]['duration_s']}
        for mode in ('STATIC', 'AGENTIC'):
            a, req, rv = reviewed_of(name, mode)
            if not a:
                row[mode] = None
                continue
            log = rv.get('log') or {}
            subs = log.get('sub_clips') or []
            row[mode] = {**usage_row(a), 'plain_fallback': a.get('plain_fallback'), 'status': rv['status'], 'pieces': len(subs), 'notes': len(rv['gaps']),
                         'empty_doubt_fields': sum(1 for s in subs for k in ('visual_action_uncertainty', 'sub_clip_uncertainty') if s.get(k) in EMPTY),
                         'overview': log.get('clip_overview'), 'piece_lines': [f"{s['max_usable_window']['in_s']:.1f}-{s['max_usable_window']['out_s']:.1f} s, grade {s['usability_grade']}: {s['visual_action_observed']}" for s in subs]}
        t4.append(row)
    res['T4'] = t4

    # T5
    by = defaultdict(list)
    for name, r in rows.items():
        by[r['mode']].append({**usage_row(r['a']), 'dur': r['clip']['duration_s']})
    res['T5'] = {m: {'clips': len(v), 'usd': round(sum(x['usd'] for x in v), 2), 'usd_per_clip': round(statistics.mean(x['usd'] for x in v), 3), 'usd_max': max(x['usd'] for x in v),
                     'seconds_per_clip': round(statistics.mean(x['seconds'] for x in v), 1), 'seconds_max': max(x['seconds'] for x in v), 'looks_per_clip': round(statistics.mean(x['looks'] for x in v), 1),
                     'tokens_in': sum(x['in'] for x in v), 'video_in': sum(x['video_in'] for x in v), 'tokens_out': sum(x['out'] for x in v), 'thinking': sum(x['thinking'] for x in v),
                     'usd_per_clip_second': round(sum(x['usd'] for x in v) / sum(x['dur'] for x in v), 4)} for m, v in by.items()}
    res['T5']['all_requests_usd'] = led['spent_usd']
    res['T5']['requests'] = len(led['requests'])

    # T6: every field, filled or empty
    fields = defaultdict(lambda: [0, 0])   # path -> [filled, empty]
    for name, log, sub in pieces:
        for path, v in leaves({k: x for k, x in sub.items() if k != 'stage15'}):
            fields['piece.' + path][0 if v not in EMPTY else 1] += 1
    for name, r in rows.items():
        for path, v in leaves({k: x for k, x in (r['rv'].get('log') or {}).items() if k not in ('sub_clips', 'max_safe_zoom_limit_applied')}):
            fields['clip.' + path][0 if v not in EMPTY else 1] += 1
    res['T6'] = {'fields': len(fields), 'always_filled': sum(1 for f, e in fields.values() if e == 0), 'always_empty': sorted(p for p, (f, e) in fields.items() if f == 0),
                 'often_empty': sorted(((p, f, e) for p, (f, e) in fields.items() if f and e and e >= f), key=lambda x: -x[2])[:40], 'table': {p: v for p, v in sorted(fields.items())}}

    # T7: the doubt and "does not show" lines
    fit = [(n, s) for n, _, s in pieces if (s['continuity_and_story'].get('primary_fit_for_beats') or s['continuity_and_story'].get('secondary_fit_for_beats'))]
    res['T7'] = {'pieces': len(pieces), 'pieces_with_a_fit': len(fit), 'fit_without_does_not_show': sum(1 for _, s in fit if s['continuity_and_story'].get('beat_fit_limits') in EMPTY),
                 'direct_fit': sum(1 for _, s in fit if s['continuity_and_story'].get('primary_fit_for_beats')),
                 'direct_fit_without_does_not_show': sum(1 for _, s in fit if s['continuity_and_story'].get('primary_fit_for_beats') and s['continuity_and_story'].get('beat_fit_limits') in EMPTY),
                 'empty_visual_action_uncertainty': sum(1 for _, _, s in pieces if s.get('visual_action_uncertainty') in EMPTY),
                 'empty_sub_clip_uncertainty': sum(1 for _, _, s in pieces if s.get('sub_clip_uncertainty') in EMPTY),
                 'fit_basis': dict(Counter(s['continuity_and_story'].get('beat_fit_basis') for _, s in fit))}

    # T8: pieces per clip
    per = Counter(n for n, _, _ in pieces)
    res['T8'] = {'pieces_per_clip': dict(sorted(Counter(per.values()).items())), 'clips_with_several': sum(1 for v in per.values() if v > 1), 'most': per.most_common(5)}

    # T10: Claude's short list, as today (the clip's overview on every piece) and with each piece's own description and "does not show" line
    multi = [(n, log, s) for n, log, s in pieces if per[n] > 1]
    overview = lambda log: next((l.split('OVERVIEW:', 1)[1].strip() for l in log.get('summary_card_lines') or [] if 'OVERVIEW:' in l), log.get('clip_overview') or '')
    add_chars = sum(len(s.get('visual_action_observed') or '') + len(s['continuity_and_story'].get('beat_fit_limits') or '') for _, _, s in pieces)
    today_chars = 0
    seen_clip = set()
    for n, log, s in pieces:
        row = P.sub_clip_row(BY_NAME[n], log, s, 50)
        today_chars += len(json.dumps({k: row.get(k) for k in ('sub_clip_id', 'clip_name', 'grade', 'duration_s', 'in_frame', 'out_frame', 'in_s', 'out_s', 'native_shot_size', 'effective_shot_size', 'action_peak', 'outcome_state', 'eligibility', 'min_hold_s')}))
        if n not in seen_clip:
            today_chars += len(overview(log))
            seen_clip.add(n)
    side = [{'clip': n, 'piece': s['sub_clip_id'], 'window_s': [s['max_usable_window']['in_s'], s['max_usable_window']['out_s']], 'today_the_clip_line': overview(log),
             'own_description': s.get('visual_action_observed'), 'does_not_show': s['continuity_and_story'].get('beat_fit_limits')} for n, log, s in multi[:40]]
    res['T10'] = {'pieces': len(pieces), 'pieces_in_clips_with_several': len(multi), 'clips_with_several': res['T8']['clips_with_several'],
                  'short_list_chars_today': today_chars, 'chars_added': add_chars, 'growth_percent': round(100 * add_chars / max(today_chars, 1)), 'side_by_side': side}

    # T11: written and read by nothing
    notes_clips = [(n, r['rv']['log'].get('clip_level_notes_for_editor')) for n, r in rows.items() if (r['rv'].get('log') or {}).get('clip_level_notes_for_editor')]
    speech = [(n, s['people_and_speaker_analysis']['speech_translation_block']) for n, _, s in pieces if s['people_and_speaker_analysis'].get('speech_translation_block')]
    defects = [(n, d) for n, _, s in pieces for d in (s.get('technical_qc_and_remediation') or {}).get('defects_detected') or []]
    res['T11'] = {'clips_with_editor_notes': len(notes_clips), 'editor_note_lines': sum(len(x) for _, x in notes_clips), 'editor_note_examples': [f'{n}: {x[0]}' for n, x in notes_clips[:8]],
                  'pieces_with_spoken_words': len(speech), 'spoken_facts': sum(len(b.get('extracted_domain_facts') or []) for _, b in speech),
                  'spoken_examples': [f"{n}: {str(b.get('english_translation'))[:200]}" for n, b in speech[:6]],
                  'pieces_with_best_frame': sum(1 for _, _, s in pieces if s.get('hero_frame_s') not in EMPTY),
                  'pieces_with_title_zone': sum(1 for _, _, s in pieces if s['pacing_and_flow'].get('text_safe_zone')),
                  'graphics_ideas': sum(len(s.get('vfx_and_graphics_opportunities') or []) for _, _, s in pieces), 'graphics_examples': [f"{n}: {(s.get('vfx_and_graphics_opportunities') or [{}])[0].get('what_and_why')}" for n, _, s in pieces if s.get('vfx_and_graphics_opportunities')][:5],
                  'defects': len(defects), 'defect_kinds': Counter(str(d.get('defect')) for _, d in defects).most_common(8),
                  'colour_groups': dict(Counter((r['rv'].get('log') or {}).get('color_match_group_id') for r in rows.values()))}

    # T12: clips whose pieces differ, so that marking the whole clip for the library is wrong either way (counted by the model's own fields; the true-in-any-film mark needs a person)
    mixed = []
    for n in per:
        subs = [s for m, _, s in pieces if m == n]
        if len(subs) > 1:
            sig = {(tuple(s['continuity_and_story'].get('primary_fit_for_beats') or []), s['continuity_and_story'].get('process_stage'), s['shot_role'], s['stage15']['visual_eligibility'].startswith('ELIGIBLE')) for s in subs}
            if len(sig) > 1:
                mixed.append({'clip': n, 'pieces': len(subs), 'different_kinds': len(sig), 'direct_fits': sorted({b for s in subs for b in s['continuity_and_story'].get('primary_fit_for_beats') or []})})
    res['T12'] = {'clips_with_several_pieces': res['T8']['clips_with_several'], 'clips_whose_pieces_differ': len(mixed), 'examples': mixed[:12]}

    # T13: fit by paragraph
    beats = script.get('beats') or []
    sent = {b['beat_id']: len([x for x in re.split(r'(?<=[.!?])\s+', b['text'].strip()) if x]) for b in beats}
    direct = Counter(b for _, _, s in pieces for b in s['continuity_and_story'].get('primary_fit_for_beats') or [])
    res['T13'] = {'paragraphs': len(beats), 'with_more_than_one_sentence': sum(1 for v in sent.values() if v > 1), 'sentences': sum(sent.values()), 'sentences_per_paragraph': sent,
                  'direct_fit_pieces_per_paragraph': dict(direct), 'direct_fits_into_a_paragraph_of_several_sentences': sum(v for b, v in direct.items() if sent.get(b, 1) > 1)}

    # T14: pauses, by arithmetic: a piece that fits a paragraph directly and whose "must not be cut away" moment is longer than the longest sentence of that paragraph
    narration = json.loads((R.RUN_DIR / 'work/options/narration.json').read_text(encoding='utf-8'))
    beats_t = json.loads((R.RUN_DIR / 'work/options/beats.json').read_text(encoding='utf-8'))
    fps = float(Fraction(str(narration.get('fps') or 50)))
    sent_len = defaultdict(list)
    for s in narration['sentences']:
        b = next((x['beat_id'] for x in beats_t if x['timeline_start_frame'] <= s['start_frame'] < x['timeline_end_frame']), None)
        sent_len[b].append(round((s['end_frame'] - s['start_frame']) / fps, 2))
    pauses = []
    for n, _, s in pieces:
        peak = s.get('must_include_action_peak')
        if not peak or not s['stage15']['visual_eligibility'].startswith('ELIGIBLE'):
            continue
        for b in s['continuity_and_story'].get('primary_fit_for_beats') or []:
            longest = max(sent_len.get(b) or [0])
            need = round(float(peak['duration_s']) - longest, 2)
            if longest and need > 0:
                pauses.append({'clip': n, 'piece': s['sub_clip_id'], 'paragraph': b, 'moment_s': peak['duration_s'], 'longest_sentence_s': longest, 'pause_needed_s': need})
    res['T14'] = {'sentence_seconds_per_paragraph': dict(sent_len), 'pieces_whose_moment_outlasts_every_sentence': len(pauses), 'within_4_s': sum(1 for p in pauses if p['pause_needed_s'] <= 4),
                  'within_7_s': sum(1 for p in pauses if p['pause_needed_s'] <= 7), 'over_7_s': sum(1 for p in pauses if p['pause_needed_s'] > 7), 'examples': sorted(pauses, key=lambda p: -p['pause_needed_s'])[:10],
                  'moments_logged': sum(1 for _, _, s in pieces if s.get('must_include_action_peak')), 'moment_seconds': sorted(round(float(s['must_include_action_peak']['duration_s']), 1) for _, _, s in pieces if s.get('must_include_action_peak'))}

    # T9 material: six clips of different kinds, the model's main facts for a person to mark
    def kind(pred):
        return next((n for n, r in sorted(rows.items(), key=lambda x: x[1]['clip']['duration_s']) if pred(n, r) and n not in chosen), None)
    chosen = []
    subs_of = lambda n: [s for m, _, s in pieces if m == n]
    for label, pred in (('a short clip (15 s or less)', lambda n, r: r['mode'] == 'STATIC' and len(subs_of(n)) == 1),
                        ('an action in several pieces', lambda n, r: len(subs_of(n)) >= 3),
                        ('speech is heard', lambda n, r: any(s['people_and_speaker_analysis'].get('speech_translation_block') for s in subs_of(n))),
                        ('flagged for a risk', lambda n, r: any(s.get('risk_flags') for s in subs_of(n))),
                        ('the longest clip', lambda n, r: r['clip']['duration_s'] == max(x['clip']['duration_s'] for x in rows.values())),
                        ('a clip of middle length watched the look-again way', lambda n, r: r['mode'] == 'AGENTIC' and 20 < r['clip']['duration_s'] < 35)):
        n = kind(pred)
        if n:
            chosen.append(n)
            log = rows[n]['rv']['log']
            res.setdefault('T9', []).append({'kind': label, 'clip': n, 'seconds': rows[n]['clip']['duration_s'], 'way': rows[n]['mode'], 'overview': log.get('clip_overview'), 'sound': log.get('audio_observed'),
                                             'pieces': [{'from_to_s': [s['max_usable_window']['in_s'], s['max_usable_window']['out_s']], 'what': s.get('visual_action_observed'), 'not_sure': s.get('visual_action_uncertainty'),
                                                         'does_not_show': s['continuity_and_story'].get('beat_fit_limits'), 'people': s['people_and_speaker_analysis'].get('people_count'),
                                                         'speech': (s['people_and_speaker_analysis'].get('speech_translation_block') or {}).get('english_translation'),
                                                         'who_speaks': (s['people_and_speaker_analysis'].get('speech_translation_block') or {}).get('speaker_role'),
                                                         'moment_s': [(s.get('must_include_action_peak') or {}).get('in_s'), (s.get('must_include_action_peak') or {}).get('out_s')]} for s in subs_of(n)]})
    (OUT / 'checks.json').write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding='utf-8')
    brief_out = {k: ({kk: vv for kk, vv in v.items() if kk not in ('table', 'side_by_side')} if isinstance(v, dict) else v) for k, v in res.items() if k not in ('T4', 'T9')}
    print(json.dumps(brief_out, indent=1, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
