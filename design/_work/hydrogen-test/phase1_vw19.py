"""Phase 1 (14 Nov 2026), after the sentence-fit run: the answers checked by the server's own code, the richer list per sentence (test 4), how steady
the fit is (test 3), today's cut per sentence, and the pause arithmetic by sentence. No model call, no cost.
Reads model-test/out-vw19-hydrogen-sentences/ and VW-19's run folder; writes model-test/out-vw19-phase1/.   python -X utf8 phase1_vw19.py"""
import json
import re
from collections import Counter, defaultdict
from fractions import Fraction

import run_vw19_hydrogen as R
import sentences_vw19_hydrogen as S
from app import analysis

OUT = R.HERE / 'out-vw19-phase1'
LINE = re.compile(r'(BEAT_\d\d)\D{0,6}?(\d+(?:\.\d+)?)\s*(?:-|to|–)\s*(\d+(?:\.\d+)?)\s*s?\W{0,4}(EXACT|PARTLY|RELATED)\W*(.*)', re.S)
RANK = {'EXACT': 0, 'PARTLY': 1, 'RELATED': 2}
BY_NAME = {c['name']: c for c in S.clips}
narration = json.loads((R.RUN_DIR / 'work/options/narration.json').read_text(encoding='utf-8'))
SENT = [{'id': f'BEAT_{i:02d}', 'n': i, 'text': s['text'], 'seconds': round((s['end_frame'] - s['start_frame']) / 50, 2), 'first': int(s['first_word_id'][1:]), 'last': int(s['last_word_id'][1:])}
        for i, s in enumerate(narration['sentences'], 1)]


def lines_of(text):
    """The lines of a fit field, one per sentence: cut at each beat id."""
    parts = re.split(r'(?=BEAT_\d\d)', str(text or ''))
    return [p.strip(' \n;/|-') for p in parts if p.strip().startswith('BEAT_')]


def pieces_of(name, suffix=''):
    p = S.OUT / f'{name}{suffix}.response.json'
    if not p.exists():
        return None
    a = json.loads(p.read_text(encoding='utf-8'))
    req = analysis.build_request(S.run, S.procedure, S.brief, S.SCRIPT, BY_NAME[name], S.POL)
    rv = analysis.review_response(a['raw'], req)
    out = {'status': rv['status'], 'thrown_out': len(rv['excluded_sub_clips']), 'notes': len(rv['gaps']), 'plain_fallback': a.get('plain_fallback'), 'pieces': []}
    for sub in (rv.get('log') or {}).get('sub_clips') or []:
        story, w = sub['continuity_and_story'], sub['max_usable_window']
        missing = {m.group(1): l[len(m.group(1)):].strip(' :,-') for l in lines_of(story.get('beat_fit_limits')) for m in [re.match(r'(BEAT_\d\d)', l)] if m}
        fits, unread = [], 0
        for l in lines_of(story.get('beat_fit_reasoning')):
            m = LINE.match(l)
            if not m:
                unread += 1
                continue
            fits.append({'sentence': m.group(1), 'from_s': float(m.group(2)), 'to_s': float(m.group(3)), 'match': m.group(4), 'why': ' '.join(m.group(5).split())[:400], 'missing': missing.get(m.group(1), '')})
        peak = sub.get('must_include_action_peak') or {}
        out['pieces'].append({'clip': name, 'piece': sub['sub_clip_id'], 'window_s': [w['in_s'], w['out_s']], 'grade': sub['usability_grade'], 'allowed': sub['stage15']['visual_eligibility'],
                              'what': sub.get('visual_action_observed'), 'not_sure': sub.get('visual_action_uncertainty'), 'primary': story.get('primary_fit_for_beats') or [],
                              'secondary': story.get('secondary_fit_for_beats') or [], 'fits': fits, 'fit_lines_unread': unread, 'moment_s': [peak.get('in_s'), peak.get('out_s')] if peak else None,
                              'shot_size': sub['camera_and_optics']['native_shot_size'], 'defects': len((sub.get('technical_qc_and_remediation') or {}).get('defects_detected') or []),
                              'limits_raw': story.get('beat_fit_limits')})
    return out


def todays_cut():
    opts = json.loads((R.RUN_DIR / 'out/options.json').read_text(encoding='utf-8'))['options']
    ids = {c['id']: c for c in S.clips}
    rows = []
    for b in opts:
        for e in b['events']:
            cid = (e.get('sub_clip_id') or '').split(':')[0]
            c = ids.get(cid)
            if not c:
                continue
            fps = float(Fraction(str(c['fps'])))
            w = int(e['illustrates_word_id'][1:])
            s = next(x for x in SENT if x['first'] <= w <= x['last'])
            rows.append({'sentence': s['id'], 'clip': c['name'], 'from_s': round(e['source_in_frame'] / fps, 2), 'to_s': round(e['source_out_frame'] / fps, 2), 'match': e.get('match')})
    return rows


def main():
    OUT.mkdir(exist_ok=True)
    res, allp = {}, []
    answered = {n: pieces_of(n) for n in BY_NAME}
    answered = {n: a for n, a in answered.items() if a}
    for a in answered.values():
        allp += a['pieces']
    ledger = [json.loads(x) for x in (S.OUT / 'ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    ok = [r for r in ledger if not r.get('error')]
    res['run'] = {'clips': len(BY_NAME), 'answered': len(answered), 'missing': sorted(n for n in BY_NAME if n not in answered), 'requests': len(ledger), 'failed': Counter(f"{r['error']} {r.get('http_status') or ''}".strip() for r in ledger if r.get('error')),
                  'plain_fallback': sorted(n for n, a in answered.items() if a['plain_fallback']), 'usd': round(sum(r.get('usd') or 0 for r in ledger), 2),
                  'usd_per_clip': round(sum(r['usd'] for r in ok) / max(len(ok), 1), 3), 'seconds_per_clip': round(sum(r['seconds'] for r in ok) / max(len(ok), 1)), 'looks_per_clip': round(sum(r.get('looks') or 0 for r in ok) / max(len(ok), 1), 1),
                  'answer_status': Counter(a['status'] for a in answered.values()), 'pieces': len(allp), 'pieces_thrown_out': sum(a['thrown_out'] for a in answered.values()), 'check_notes': sum(a['notes'] for a in answered.values()),
                  'allowed': Counter(p['allowed'] for p in allp)}
    good = [p for p in allp if p['allowed'].startswith('ELIGIBLE')]
    res['fit'] = {'allowed_pieces': len(good), 'with_a_primary_sentence': sum(1 for p in good if p['primary']), 'with_any_fit_line': sum(1 for p in good if p['fits']), 'fit_lines': sum(len(p['fits']) for p in good),
                  'fit_lines_not_in_the_asked_form': sum(p['fit_lines_unread'] for p in good), 'by_match': Counter(f['match'] for p in good for f in p['fits']),
                  'exact_without_missing_line': sum(1 for p in good for f in p['fits'] if f['match'] == 'EXACT' and not f['missing']),
                  'primary_but_no_exact_line': sum(1 for p in good for b in p['primary'] if not any(f['sentence'] == b and f['match'] == 'EXACT' for f in p['fits'])),
                  'fit_seconds_outside_the_piece': sum(1 for p in good for f in p['fits'] if f['from_s'] < p['window_s'][0] - 0.3 or f['to_s'] > p['window_s'][1] + 0.3)}
    # ---- the richer list, per sentence ----
    cut = todays_cut()
    listing = []
    for s in SENT:
        cands = [{**{k: p[k] for k in ('clip', 'piece', 'window_s', 'grade', 'what', 'shot_size', 'moment_s', 'defects')}, **f} for p in good for f in p['fits'] if f['sentence'] == s['id']]
        cands.sort(key=lambda c: (RANK[c['match']], 'ABC'.find(c['grade']) if c['grade'] in 'ABC' else 9, -(c['to_s'] - c['from_s'])))
        listing.append({**{k: s[k] for k in ('id', 'n', 'text', 'seconds')}, 'candidates': cands, 'today': [c for c in cut if c['sentence'] == s['id']]})
    res['per_sentence'] = [{'sentence': s['n'], 'seconds': s['seconds'], 'exact': sum(1 for c in s['candidates'] if c['match'] == 'EXACT'), 'partly': sum(1 for c in s['candidates'] if c['match'] == 'PARTLY'),
                            'related': sum(1 for c in s['candidates'] if c['match'] == 'RELATED'), 'today': [f"{c['clip'][:5]} {c['from_s']}-{c['to_s']}" for c in s['today']] or ['blank']} for s in listing]
    (OUT / 'list.json').write_text(json.dumps(listing, indent=1, ensure_ascii=False), encoding='utf-8')
    md = ['# The pieces offered for each sentence (from Gemini 4 Hydrogen\'s answers)', '',
          'Each sentence with its candidate pieces, best first: EXACT (the picture shows exactly what the sentence says), then PARTLY, then RELATED. Seconds are seconds of the clip.', '']
    for s in listing:
        md += [f"## Sentence {s['n']} ({s['seconds']} s)", '', f"> {s['text']}", '']
        if not s['candidates']:
            md += ['No piece is offered for this sentence.', '']
            continue
        md += ['| # | Clip | Seconds | Match | Grade | Shot | What the piece shows | What is missing | Why |', '|---|---|---|---|---|---|---|---|---|']
        cell = lambda t: ' '.join(str(t or '').split()).replace('|', '/')
        for i, c in enumerate(s['candidates'][:12], 1):
            md.append(f"| {i} | {c['clip'][:5]} | {c['from_s']:.1f} to {c['to_s']:.1f} | {c['match']} | {c['grade']} | {c['shot_size']} | {cell(c['what'])[:260]} | {cell(c['missing'])[:200]} | {cell(c['why'])[:200]} |")
        if len(s['candidates']) > 12:
            md.append(f"\n{len(s['candidates']) - 12} more candidates are in list.json.")
        md.append('')
    (OUT / 'list.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    res['list'] = {'chars_md': len('\n'.join(md)), 'candidates': sum(len(s['candidates']) for s in listing), 'sentences_with_an_exact_piece': sum(1 for s in listing if any(c['match'] == 'EXACT' for c in s['candidates'])),
                   'sentences_with_no_piece': [s['n'] for s in listing if not s['candidates']]}
    # ---- test 3: the same clip sent twice ----
    twice = []
    for name in BY_NAME:
        b = pieces_of(name, '.2')
        if not b or name not in answered:
            continue
        sig = lambda a: {(f['sentence'], f['match']) for p in a['pieces'] if p['allowed'].startswith('ELIGIBLE') for f in p['fits']}
        x, y = sig(answered[name]), sig(b)
        ex = lambda q: sorted({s for s, m in q if m == 'EXACT'})
        twice.append({'clip': name[:5], 'pieces_run1': len(answered[name]['pieces']), 'pieces_run2': len(b['pieces']), 'exact_run1': ex(x), 'exact_run2': ex(y), 'same_exact_sentences': ex(x) == ex(y),
                      'fits_in_both': len(x & y), 'fits_in_one_only': len(x ^ y)})
    res['twice'] = twice
    # ---- pauses by sentence: an EXACT piece whose "moment that must not be cut" is longer than its sentence ----
    secs = {s['id']: s['seconds'] for s in SENT}
    pauses = [{'sentence': f['sentence'], 'clip': p['clip'][:5], 'moment_s': round(p['moment_s'][1] - p['moment_s'][0], 1), 'sentence_s': secs[f['sentence']], 'pause_s': round(p['moment_s'][1] - p['moment_s'][0] - secs[f['sentence']], 1)}
              for p in good if p['moment_s'] and p['moment_s'][0] is not None for f in p['fits'] if f['match'] == 'EXACT' and f['sentence'] in secs and (p['moment_s'][1] - p['moment_s'][0]) > secs[f['sentence']]]
    res['pauses'] = {'exact_pieces_whose_moment_outlasts_the_sentence': len(pauses), 'rows': sorted(pauses, key=lambda r: -r['pause_s'])[:12]}
    res['today'] = cut
    (OUT / 'phase1.json').write_text(json.dumps(res, indent=1, ensure_ascii=False, default=str), encoding='utf-8')
    print(json.dumps({k: v for k, v in res.items() if k != 'today'}, indent=1, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
