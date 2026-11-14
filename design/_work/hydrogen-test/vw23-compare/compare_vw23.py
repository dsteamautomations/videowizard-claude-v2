"""VW-23: the cut of 13 Nov (Gemini 3.8 Flash, fit by paragraph) against the cut of 14 Nov (Gemini 4 Hydrogen, fit by sentence), same scenes and narration.
Reads the files fetched from the server into vw23cmp/ (read only) and the operator's answers (given below, read from the run's log). No model call.
  python -X utf8 compare_vw23.py"""
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

D = Path(__file__).parent / 'vw23cmp'
load = lambda n: json.loads((D / n).read_text(encoding='utf-8'))
doc = lambda d: d.get('document') or d
OLD_ANS = {'1.1': 'KEEP', '10.1': 'KEEP', '10.2': 'KEEP', '10.3': 'KEEP', '10.4': 'KEEP', '11.1': 'KEEP', '11.2': 'KEEP', '12.1': 'KEEP', '13.1': 'KEEP', '14.1': 'KEEP', '14.3': 'KEEP', '14.4': 'KEEP',
           '15.1': 'KEEP', '2.1': 'KEEP', '3.2': 'REJECT', '3.2A1': 'KEEP', '3.4': 'KEEP', '4.1': 'KEEP', '5.2': 'KEEP', '5.3': 'KEEP', '5.5': 'KEEP', '5.6': 'KEEP', '5.7': 'REJECT', '6.1': 'KEEP',
           '6.2': 'KEEP', '7.1': 'KEEP', '7.2': 'KEEP', '7.3': 'KEEP', '7.4': 'KEEP', '7.5': 'KEEP', '8.1': 'KEEP', '8.2': 'REJECT', '8.2A1': 'KEEP', '8.3': 'KEEP', '8.4': 'REJECT', '8.4A1': 'KEEP',
           '8.5': 'KEEP', '8.6': 'KEEP', '9.1': 'REJECT', '9.1A1': 'KEEP', '9.2': 'KEEP'}
NEW_ANS = {'1.1': 'KEEP', '10.1': 'KEEP', '10.2': 'KEEP', '10.3': 'KEEP', '10.4': 'KEEP', '11.1': 'KEEP', '11.2': 'KEEP', '12.1': 'KEEP', '12.2': 'KEEP', '13.1': 'KEEP', '14.2': 'KEEP', '15.1': 'KEEP',
           '2.1': 'KEEP', '2.2': 'KEEP', '3.2': 'KEEP', '3.4': 'KEEP', '4.1': 'KEEP', '5.2': 'KEEP', '5.4': 'KEEP', '5.5': 'KEEP', '5.6': 'REJECT', '6.1': 'KEEP', '6.2': 'KEEP', '7.1': 'KEEP',
           '7.2': 'KEEP', '7.3': 'KEEP', '7.4': 'KEEP', '7.5': 'KEEP', '8.1': 'KEEP', '8.2': 'KEEP', '8.3': 'KEEP', '8.4': 'KEEP', '8.5': 'KEEP', '9.1': 'REJECT', '9.1A1': 'KEEP', '9.2': 'KEEP'}


def cut(name, options_file, package_file, answers):
    pk, opts = doc(load(package_file)), doc(load(options_file))['options']
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    beats = {b['beat_id']: b for b in pk['beats']}
    fps = pk['timeline']['fps']
    shots, sentences = [], {}
    for scene_n, o in enumerate(sorted(opts, key=lambda o: o['option_number']), 1):
        b = beats[o['beat_id']]
        cursor = b['timeline_start_frame']
        for k, e in enumerate(o['events'], 1):
            slide = f'{scene_n}.{k}'
            if e.get('blank'):
                n = int(e['timeline_frames'])
                shots.append({'slide': slide, 'scene': scene_n, 'blank': True, 'start': cursor, 'frames': n, 'intent': e.get('intent'), 'answer': answers.get(slide)})
            else:
                r = rows[e['sub_clip_id']]
                src = Fraction(str(r['source_fps']))
                n = int(round((e['source_out_frame'] - e['source_in_frame']) * Fraction(fps) / src / Fraction(str(e.get('fps_ratio') or 1))))
                shots.append({'slide': slide, 'scene': scene_n, 'blank': False, 'start': cursor, 'frames': n, 'clip': r['clip_name'], 'piece': e['sub_clip_id'], 'match': e.get('match'),
                              'in_s': round(float(e['source_in_frame'] / src), 2), 'out_s': round(float(e['source_out_frame'] / src), 2), 'piece_s': r['duration_s'],
                              'what': r.get('what'), 'size': r.get('native_shot_size'), 'grade': r.get('grade'), 'answer': answers.get(slide), 'alt_answer': answers.get(slide + 'A1'),
                              'alternatives': len(e.get('alternatives') or []), 'note': (e.get('note') or {}).get('kind'),
                              'fits': {f['step_id']: f['match'] for f in r.get('sentence_fits') or [] if f.get('step_id')}})
            cursor += n
        assert abs(cursor - b['timeline_end_frame']) <= 3, (name, o['beat_id'], cursor, b['timeline_end_frame'])
        for s in b['steps']:
            sentences[s['step_id']] = {'scene': scene_n, 'text': s['text'], 'start': s['start_frame'], 'end': s['end_frame'], 'shots': []}
    for sh in shots:   # a shot belongs to every sentence it overlaps by at least half a second
        for sid, s in sentences.items():
            if min(sh['start'] + sh['frames'], s['end']) - max(sh['start'], s['start']) >= fps // 2:
                s['shots'].append(sh)
    return {'name': name, 'fps': fps, 'shots': shots, 'sentences': sentences, 'pieces': len(rows), 'total': sum(b['target_beat_frames'] for b in pk['beats'])}


def measures(c):
    fps, shots = c['fps'], c['shots']
    foot = [s for s in shots if not s['blank']]
    blank = [s for s in shots if s['blank']]
    sec = lambda xs: round(sum(x['frames'] for x in xs) / fps, 1)
    kept = [s for s in foot if s['answer'] == 'KEEP' or (s['answer'] == 'REJECT' and s['alt_answer'] == 'KEEP')]
    clips = Counter(s['clip'] for s in foot)
    return {'film_s': round(c['total'] / fps, 1), 'footage_s': sec(foot), 'blank_s': sec(blank), 'footage_share': round(100 * sum(x['frames'] for x in foot) / c['total'], 1),
            'footage_shots': len(foot), 'blanks': len(blank), 'direct': sum(1 for s in foot if s['match'] == 'direct'), 'b_roll': sum(1 for s in foot if s['match'] == 'b_roll'),
            'library': sum(1 for s in foot if s['match'] == 'library'),
            'answered': Counter(s['answer'] for s in foot), 'rejected_then_alternative_kept': sum(1 for s in foot if s['answer'] == 'REJECT' and s['alt_answer'] == 'KEEP'),
            'footage_s_kept_as_placed': sec([s for s in foot if s['answer'] == 'KEEP']), 'footage_s_kept_incl_alternative': sec(kept), 'blank_answers': Counter(s['answer'] for s in blank),
            'shots_under_3s': sum(1 for s in foot if s['frames'] / fps < 3), 'shot_seconds_median': sorted(round(s['frames'] / fps, 1) for s in foot)[len(foot) // 2] if foot else 0,
            'shots_from_inside_a_longer_piece': sum(1 for s in foot if (s['out_s'] - s['in_s']) < 0.5 * float(s['piece_s'] or 0)),
            'different_clips': len(clips), 'clips_used_more_than_once': {k[:8]: v for k, v in clips.items() if v > 1}, 'pieces_offered': c['pieces'],
            'per_scene_footage_s': {n: sec([s for s in foot if s['scene'] == n]) for n in sorted({s['scene'] for s in shots})}}


def main():
    old = cut('13 Nov, Flash', 'options-v1.json', 'package-old.json', OLD_ANS)
    new = cut('14 Nov, Hydrogen', 'options-v2.json', 'package-new.json', NEW_ANS)
    res = {'old': measures(old), 'new': measures(new)}
    oc, nc = {s['clip'] for s in old['shots'] if not s['blank']}, {s['clip'] for s in new['shots'] if not s['blank']}
    res['clips'] = {'in_both': len(oc & nc), 'only_old': sorted(c[:8] for c in oc - nc), 'only_new': sorted(c[:8] for c in nc - oc)}
    # per sentence: footage or blank in each cut
    rows = []
    for sid, so in old['sentences'].items():
        sn = new['sentences'][sid]
        kind = lambda s: 'footage' if any(not x['blank'] for x in s['shots']) else 'blank'
        fo, fn = [x for x in so['shots'] if not x['blank']], [x for x in sn['shots'] if not x['blank']]
        rows.append({'sentence': sid, 'scene': so['scene'], 'text': so['text'], 'old': kind(so), 'new': kind(sn),
                     'old_shots': [{k: x.get(k) for k in ('slide', 'clip', 'in_s', 'out_s', 'match', 'size', 'answer', 'alt_answer', 'what')} for x in fo],
                     'new_shots': [{**{k: x.get(k) for k in ('slide', 'clip', 'in_s', 'out_s', 'match', 'size', 'answer', 'alt_answer', 'what')}, 'gemini': x['fits'].get(sid)} for x in fn],
                     'same_clips': [x['clip'] for x in fo] == [x['clip'] for x in fn], 'same_set_other_order': sorted(x['clip'] for x in fo) == sorted(x['clip'] for x in fn) and [x['clip'] for x in fo] != [x['clip'] for x in fn]})
    res['sentences'] = {'count': len(rows), 'footage_in_both': sum(1 for r in rows if r['old'] == r['new'] == 'footage'), 'blank_in_both': sum(1 for r in rows if r['old'] == r['new'] == 'blank'),
                        'gained_footage': [r['sentence'] for r in rows if r['old'] == 'blank' and r['new'] == 'footage'], 'lost_footage': [r['sentence'] for r in rows if r['old'] == 'footage' and r['new'] == 'blank'],
                        'same_clips_both': sum(1 for r in rows if r['old'] == r['new'] == 'footage' and r['same_clips']),
                        'two_or_more_shots': {'old': sum(1 for r in rows if len(r['old_shots']) > 1), 'new': sum(1 for r in rows if len(r['new_shots']) > 1)}}
    # the new cut's direct shots against Gemini's own mark for the sentence they sit under
    marks = Counter()
    for sid, s in new['sentences'].items():
        for x in s['shots']:
            if not x['blank'] and x['match'] == 'direct':
                marks[x['fits'].get(sid) or 'no fit for this sentence'] += 1
    res['new_direct_shots_by_gemini_mark'] = dict(marks)
    (D.parent / 'compare.json').write_text(json.dumps({**res, 'rows': rows}, indent=1, ensure_ascii=False, default=str), encoding='utf-8')
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))


if __name__ == '__main__':
    main()
