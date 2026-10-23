"""Mechanical judge for options (2A) and master (2B): grammar G1–G17, editor rules R*, QC Q1–Q8 (design/15 §3 + design/17 §2).
Returns {'refusals': [...], 'flags': [...]}: a refusal rejects the proposal; a flag is shown to the operator."""
import re
from fractions import Fraction

from .package import SHOT_SIZES, GRID
from .slides import DECISION_KINDS

ROLL_SPEAKER = 'ELIGIBLE_A_ROLL_SPEAKER'
MIN_BLANK_S = 3      # design/21: a blank (AI video or animation) is at least 3 s
LONG_BLANK_S = 12    # design/85 G1: a blank over this is a long run of AI pictures; the planner looks for a real cut-in first


def long_blank_flag(k, tl_fps, tag):
    """design/85 G1: E2, a flag not a refusal."""
    if k > LONG_BLANK_S * tl_fps:
        return f'{tag}: E2 blank of {k / tl_fps:.1f} s is over {LONG_BLANK_S} s: a run of AI pictures that long reads as synthetic; find a footage cut-in, a B-roll clip or a frame that relates and split it, or say in intent why it must stay whole'
    return None
LONG_REAL_S = 4      # design/21 rule 11: a real shot longer than this must earn its length
NEUTRAL = ('Toward_Lens', 'Away', 'Neutral')


def _tl_frames(ev, row, timeline_fps):
    """Source frames → timeline frames: exact when the fps ratio is integer, else nearest frame (design/17 A46)."""
    ratio = Fraction(str(timeline_fps)) / Fraction(row['source_fps'])
    n = ev['source_out_frame'] - ev['source_in_frame']
    return int(round(n * ratio)), ratio


def _eye_ok(a, b):
    if a == b or b is None or a is None:
        return True
    try:
        ia, ib = GRID.index(a), GRID.index(b)
    except ValueError:
        return True
    return abs(ia // 3 - ib // 3) <= 1 and abs(ia % 3 - ib % 3) <= 1   # adjacent cells count as a match


def validate_options(doc, package, policy):
    refusals, flags = [], []
    rows = {r['sub_clip_id']: r for r in package['sub_clips']}
    beats = {b['beat_id']: b for b in package['beats']}
    tl_fps = package['timeline']['fps']
    opts = doc.get('options') or []
    gaps = {g['beat_id'] for g in doc.get('gaps') or []}
    numbers = [o.get('option_number') for o in opts]
    if numbers != list(range(1, len(opts) + 1)):
        refusals.append('G12: option numbers must run 1..N in order')
    by_beat = {}
    for o in opts:
        by_beat.setdefault(o.get('beat_id'), []).append(o)
    for bid in beats:
        if bid not in by_beat and bid not in gaps:
            refusals.append(f'{bid}: no option and not declared as a gap')
    for bid, group in by_beat.items():
        if bid not in beats:
            refusals.append(f'unknown beat {bid}')
            continue
        ranks = [o.get('rank') for o in group]
        if ranks[0] != 'PRIMARY' or ranks.count('PRIMARY') != 1 or len(group) > 2 or (len(group) == 2 and ranks[1] != 'SECONDARY'):
            refusals.append(f'G12: {bid} needs one PRIMARY first and at most one SECONDARY')
        if len(group) == 2:
            a = [(e.get('sub_clip_id'), e.get('source_in_frame'), e.get('source_out_frame')) for e in group[0].get('events', []) if not e.get('blank')]
            b = [(e.get('sub_clip_id'), e.get('source_in_frame'), e.get('source_out_frame')) for e in group[1].get('events', []) if not e.get('blank')]
            sizes_a = [rows[e['sub_clip_id']]['effective_shot_size'] for e in group[0].get('events', []) if e.get('sub_clip_id') in rows]
            sizes_b = [rows[e['sub_clip_id']]['effective_shot_size'] for e in group[1].get('events', []) if e.get('sub_clip_id') in rows]
            if {x[0] for x in a} == {x[0] for x in b} and sizes_a == sizes_b:
                refusals.append(f'G13: {bid} SECONDARY must differ from PRIMARY in sub-clips or shot sizes')
    words = {w['id']: w for w in (package.get('narration') or {}).get('words') or []}
    silences = (package.get('narration') or {}).get('silences') or []
    uses = {}    # clip_id -> [(option_number, beat_id, event_index, has_reuse_decision)] in film order (design/21 rule 7)
    for o in opts:
        n, bid, events = o.get('option_number'), o.get('beat_id'), o.get('events') or []
        beat = beats.get(bid)
        if not beat or not events:
            refusals.append(f'OPTION #{n}: needs a beat and at least one event')
            continue
        if not str(o.get('reasoning') or '').strip() or not o.get('log_fields_cited'):
            refusals.append(f'OPTION #{n}: reasoning and log_fields_cited are required')
        if not (o.get('best_unchosen') or {}).get('rule'):
            refusals.append(f'OPTION #{n}: R15 best_unchosen with the excluding rule is required')
        total = 0
        prev = None
        sizes = []
        cursor = beat['timeline_start_frame']
        for i, ev in enumerate(events):
            if ev.get('blank'):   # design/21: a stretch left for AI video or animation; the narration runs on
                k = ev.get('timeline_frames')
                tag = f'OPTION #{n} blank at event {i + 1}'
                if not isinstance(k, int) or k <= 0:
                    refusals.append(f'{tag}: timeline_frames must be a positive whole number')
                    continue
                if not str(ev.get('intent') or '').strip():
                    refusals.append(f'{tag}: intent is required (what the AI video or animation must show)')
                if k < MIN_BLANK_S * tl_fps:
                    if str(ev.get('short_reason') or '').strip():
                        flags.append(f'{tag}: E1 blank of {k / tl_fps:.1f} s is under {MIN_BLANK_S} s; the operator decides ({ev["short_reason"]})')
                    else:
                        refusals.append(f'{tag}: E1 a blank must be at least {MIN_BLANK_S} s ({k / tl_fps:.1f} s): hold a neighbouring shot longer, or give short_reason so the operator decides')
                long = long_blank_flag(k, tl_fps, tag)
                if long:
                    flags.append(long)
                ev['_timeline_frames'], ev['_fps_ratio'] = k, '1'
                total += k
                cursor += k
                prev, sizes = None, []
                continue
            sid = ev.get('sub_clip_id')
            row = rows.get(sid)
            tag = f'OPTION #{n} shot {i + 1} ({sid})'
            if not row:
                refusals.append(f'{tag}: unknown sub-clip')
                continue
            # design/21: every real shot states how it matches the words; anything uncertain goes behind a decision slide
            d = ev.get('decision')
            if d is not None and (not isinstance(d, dict) or d.get('kind') not in DECISION_KINDS or not str(d.get('question') or '').strip()):
                refusals.append(f'{tag}: decision needs kind ({", ".join(DECISION_KINDS)}) and the question for the operator')
                d = None
            if ev.get('match') not in ('direct', 'b_roll') or not str(ev.get('evidence') or '').strip():
                refusals.append(f'{tag}: match (direct or b_roll) and evidence (the log fields that show it matches the words) are required')
            if ev.get('match') == 'b_roll' and not d:
                refusals.append(f'{tag}: B-roll goes behind a decision slide (decision kind b_roll)')
            if row.get('grade') == 'C' and not d:
                refusals.append(f'{tag}: E3 the log grades this sub-clip C (poor quality): put it behind a decision slide (kind poor_quality) or leave a blank')
            uses.setdefault(row['clip_id'], []).append((n, bid, i, bool(d and d.get('kind') == 'reuse')))
            if not row['eligibility'].startswith('ELIGIBLE') or not row['client_safe'] or row['risk_flags']:
                refusals.append(f'{tag}: G10/Q8 sub-clip is not eligible or not client-safe ({row["eligibility"]}, risk flags {row["risk_flags"]})')
            if row['eligibility'] == ROLL_SPEAKER and not policy.get('show_speaker_video'):
                refusals.append(f'{tag}: Q1 speaker on screen while show_speaker_video is false')
            a, z = ev.get('source_in_frame'), ev.get('source_out_frame')
            if not (isinstance(a, int) and isinstance(z, int) and row['in_frame'] <= a < z <= row['out_frame']):
                refusals.append(f"{tag}: G1 source frames {a}-{z} must lie inside the usable window {row['in_frame']}-{row['out_frame']}")
                continue
            peak = row.get('action_peak')
            if peak and not (a <= peak['in_frame'] and peak['out_frame'] <= z):
                refusals.append(f"{tag}: G2 must_include_action_peak {peak['in_frame']}-{peak['out_frame']} dropped")
            src_fps = Fraction(row['source_fps'])
            hold_s = row['min_hold_s'] + (1.0 if row['effective_shot_size'] in ('WS', 'EWS') else 0.0) - (0.5 if row['effective_shot_size'] in ('CU', 'ECU') else 0.0)
            hold_s = max(hold_s, row['min_hold_s'])
            if (z - a) / src_fps < row['min_hold_s'] and not ev.get('hold_last_frame'):
                refusals.append(f"{tag}: G3 shorter than min_comprehension_hold_s {row['min_hold_s']}")
            elif (z - a) / src_fps < hold_s:
                flags.append(f"{tag}: R5 hold under {hold_s:.1f} s for a {row['effective_shot_size']}")
            if ev.get('hold_last_frame') and not row['still_eligible']:
                refusals.append(f'{tag}: G16 hold_last_frame only on still_frame_dynamic_zoom_eligible sub-clips')
            if ev.get('crop') == 'hands_only' and row['eligibility'] != 'ELIGIBLE_WITH_CROP':
                flags.append(f'{tag}: G17 hands-only crop requested; flagged for Smart Reframe / Magic Mask if it clips the action')
            for c in row['pairing_constraints']:
                if c.upper().startswith('MUTUALLY_EXCLUSIVE_WITH'):
                    other = c.split(':', 1)[-1].strip()
                    if any(e2.get('sub_clip_id') == other for e2 in events):
                        refusals.append(f'{tag}: G4 pairing constraint {c}')
            for iv in ev.get('a2_intervals') or []:
                if not any(ns['in_frame'] <= iv['in_frame'] < iv['out_frame'] <= ns['out_frame'] for ns in row['nat_sound']):
                    refusals.append(f"{tag}: Q6 A2 interval {iv['in_frame']}-{iv['out_frame']} is not inside a clean_nat_sound_interval")
            if row['handles']['video_handle_frames_before'] == 0 and a == row['in_frame'] and ev.get('transition_in'):
                refusals.append(f'{tag}: G9 no transition into a zero-handle edge')
            if row['natural_cut_frames'] and min(abs(a - f) for f in row['natural_cut_frames']) > 6 and a != row['in_frame']:
                flags.append(f'{tag}: R1 in-point is not at a natural cut point')
            if row['accent_frames'] and all(f > z or f < a for f in row['accent_frames']):
                flags.append(f'{tag}: R1 no accent event inside the shot')
            n_tl, ratio = _tl_frames(ev, row, tl_fps)
            ev['_timeline_frames'] = n_tl
            ev['_fps_ratio'] = str(ratio)
            if n_tl > LONG_REAL_S * tl_fps and not str(ev.get('hold_reason') or '').strip():
                flags.append(f'{tag}: rule 11 real shot of {n_tl / tl_fps:.1f} s: cut it to the part that carries the meaning, or give hold_reason')
            total += n_tl
            if prev:
                ps, cs = prev['effective_shot_size'], row['effective_shot_size']
                if ps in SHOT_SIZES and cs in SHOT_SIZES and ps == cs:
                    sizes.append(cs)
                    flags.append(f'{tag}: G5 adjacent shots of the same size ({cs})')
                    if len(sizes) >= 2:
                        refusals.append(f'{tag}: G5 three shots of the same size in a row')
                else:
                    sizes = []
                if prev['lighting'] == 'HARD_SUN' and row['lighting'] == 'SOFT_OVERCAST' or prev['lighting'] == 'SOFT_OVERCAST' and row['lighting'] == 'HARD_SUN':
                    refusals.append(f'{tag}: G8 Hard_Sun / Soft_Overcast cut inside a beat')
                if not _eye_ok(prev['exit_eye_grid'], row['entry_eye_grid']):
                    flags.append(f"{tag}: G6 eye-trace {prev['exit_eye_grid']} → {row['entry_eye_grid']} without a neutral buffer")
                if prev['screen_direction'] not in NEUTRAL and row['screen_direction'] not in NEUTRAL and prev['screen_direction'] != row['screen_direction']:
                    refusals.append(f'{tag}: G7 screen direction flips without a neutral shot')
                if prev['color_group'] != row['color_group']:
                    flags.append(f'{tag}: R10 colour group changes inside the beat')
                if prev['energy'] > row['energy']:
                    flags.append(f'{tag}: R4 energy drops inside the beat')
                if prev['landmarks'] and row['landmarks'] and set(prev['landmarks'][:1]) == set(row['landmarks'][:1]) and i >= 2 and set(events[i - 2].get('_lm', [])) == set(row['landmarks'][:1]):
                    flags.append(f'{tag}: R8 same dominant landmark in three consecutive shots')
            ev['_lm'] = row['landmarks'][:1]
            # design/19 B1–B3: word-timed craft rules (flags)
            wid = ev.get('illustrates_word_id')
            if i > 0 and wid in words and not (words[wid]['start_frame'] - 12 <= cursor <= words[wid]['start_frame'] - 6):
                flags.append(f"{tag}: B1 pre-roll: starts at frame {cursor}, the phrase at {words[wid]['start_frame']} (aim 6-12 frames before)")
            awid = ev.get('action_word_id')
            if awid in words and row['accent_frames']:
                accents = [cursor + int(round((f - a) * ratio)) for f in row['accent_frames'] if a <= f < z]
                if accents and min(abs(x - words[awid]['start_frame']) for x in accents) > 6:
                    flags.append(f"{tag}: B2 the word {words[awid]['text']!r} is not within 6 frames of the shot's action accent")
            if i > 0 and not row['nat_sound'] and any(s['start_frame'] < cursor < s['end_frame'] for s in silences):
                flags.append(f'{tag}: B3 cuts inside a narration pause of 1.2 s or more; hold the shot or use a sub-clip with clean natural sound')
            cursor += n_tl
            prev = row
        # design/91 N17: every step the scene narrates is shown by one event, or left as a blank for visuals
        own_steps = {s['step_id']: s for s in beat.get('steps') or []}
        smap = o.get('steps')
        if smap is None:
            if own_steps:
                flags.append(f'OPTION #{n}: N17 no step map: name the event that shows each step of the scene ({", ".join(own_steps)}) (warned in this release; refused from the next)')
        else:
            seen = []
            for s in smap if isinstance(smap, list) else []:
                sid, k = (s or {}).get('step_id'), (s or {}).get('event')
                if sid not in own_steps:
                    refusals.append(f'OPTION #{n}: N17 unknown step {sid!r} for {bid}')
                    continue
                seen.append(sid)
                if not isinstance(k, int) or not 1 <= k <= len(events):
                    refusals.append(f'OPTION #{n}: N17 step {sid} names event {k}, which this option does not have')
                    continue
                e = events[k - 1]
                if e.get('blank'):
                    continue
                if not str(s.get('why') or '').strip():
                    refusals.append(f'OPTION #{n}: N17 step {sid} is shown by shot {k}: say why (the logged action, process_stage or outcome_state that shows it)')
                row = rows.get(e.get('sub_clip_id')) or {}
                if row.get('process_stage') and beat.get('process_stages') and row['process_stage'] not in beat['process_stages']:
                    flags.append(f"OPTION #{n}: N17 step {sid} ({own_steps[sid]['text'][:60]}) is shown by a clip of the stage {row['process_stage']!r}; the scene narrates "
                                 f"{', '.join(beat['process_stages'])}: the right step? (the operator decides)")
                if s.get('claim'):
                    flags.append(f"OPTION #{n}: N17 step {sid} is a claim ({own_steps[sid]['text'][:60]}) shown by footage: the shot must show its evidence or its result, "
                                 'or leave a blank for a graphic or a scene of the result')
            for sid in own_steps:
                if seen.count(sid) != 1:
                    refusals.append(f"OPTION #{n}: N17 step {sid} ({own_steps[sid]['text'][:60]}) {'is not shown' if not seen.count(sid) else 'is named twice'}: "
                                    'name the one event that shows it, or a blank for visuals')
        for kept in o.get('carries_over') or []:   # design/91 N14: the state the step before left is still visible
            for k, e in enumerate(events, 1):
                lm = (rows.get(e.get('sub_clip_id')) or {}).get('landmarks') or []
                if not e.get('blank') and not any(str(kept).lower() in str(x).lower() or str(x).lower() in str(kept).lower() for x in lm):
                    flags.append(f"OPTION #{n}: N14 shot {k} ({e.get('sub_clip_id')}) does not show {kept!r}, which the step before left (its log lists {', '.join(map(str, lm)) or 'nothing'})")
        if total != beat['target_beat_frames']:
            refusals.append(f"OPTION #{n}: G11 timeline length {total} frames must equal the beat's {beat['target_beat_frames']}")
        for i, ev in enumerate(events):
            ev.pop('_lm', None)
    # design/21 rule 7: a clip appears once in the film. Its first and backup options for one scene may share it (only one is kept);
    # any other second use, including another part of the same clip, must be a decision of kind reuse.
    for cid, us in uses.items():
        for j, (n, bid, i, is_reuse) in enumerate(us):
            earlier = [u for u in us[:j] if not (u[1] == bid and u[0] != n)]
            if earlier and not is_reuse:
                refusals.append(f'OPTION #{n} shot {i + 1}: Q4 clip {cid} is already used (option #{earlier[0][0]}); a second use, even of another part, needs a decision of kind reuse or another clip')
    # design/91 N14: consecutive scenes narrating the same process stage stay in one place unless the option names the move
    order = [b for b in package['beats'] if by_beat.get(b['beat_id'])]
    for a, b in zip(order, order[1:]):
        if not set(a.get('process_stages') or []) & set(b.get('process_stages') or []):
            continue
        oa, ob = by_beat[a['beat_id']][0], by_beat[b['beat_id']][0]
        last = next((rows.get(e.get('sub_clip_id')) for e in reversed(oa.get('events') or []) if not e.get('blank') and e.get('sub_clip_id') in rows), None)
        first = next((rows.get(e.get('sub_clip_id')) for e in ob.get('events') or [] if not e.get('blank') and e.get('sub_clip_id') in rows), None)
        if last and first and last.get('color_group') != first.get('color_group') and not str(ob.get('moves_place') or '').strip():
            flags.append(f"OPTION #{ob.get('option_number')}: N14 {a['beat_id']} and {b['beat_id']} narrate one process but cut from colour group {last.get('color_group')} "
                         f"to {first.get('color_group')}: another place mid-process; keep one place, or name the move (moves_place)")
    energies = []
    for b in package['beats']:
        group = by_beat.get(b['beat_id'])
        if group:
            es = [rows[e['sub_clip_id']]['energy'] for e in group[0].get('events', []) if e.get('sub_clip_id') in rows]
            energies.append(max(es) if es else None)
    if len(energies) >= 3 and any(energies[i] is not None and energies[i] == energies[i + 1] == energies[i + 2] for i in range(len(energies) - 2)):
        flags.append('R4: three consecutive beats with the same peak energy')
    qc = doc.get('qc_self') or {}
    for k in (f'Q{i}' for i in range(1, 9)):
        if k not in qc or 'pass' not in (qc.get(k) or {}):
            refusals.append(f'qc_self.{k} missing (the model must state pass/fail with evidence; the validator decides)')
    return {'refusals': refusals, 'flags': flags}


RULE_RE = re.compile(r'(?:^|: )(rule 11|[A-Z]\d{1,2})(?=[ :])')


def group_flags(flags):
    """design/43 7.6: the flags grouped by rule, most frequent first, three examples each (121 lines became a dozen on VW-3)."""
    groups = {}
    for f in flags:
        m = RULE_RE.search(f)
        rule = m.group(1) if m else 'other'
        g = groups.setdefault(rule, {'rule': rule, 'count': 0, 'examples': []})
        g['count'] += 1
        if len(g['examples']) < 3:
            g['examples'].append(f)
    return sorted(groups.values(), key=lambda g: (-g['count'], g['rule']))


def validate_master(master, package):
    """Q4 zero duplicate sub-clips; Q5 runtime equals the sum of beats with no gaps or 1-frame cuts; events ripple from zero."""
    refusals, flags = [], []
    seen = {}
    cursor = 0
    for ev in master['events']:
        if ev.get('kind') == 'gap':
            cursor += ev['timeline_frames']
            continue
        if ev['sub_clip_id'] in seen and not ev.get('reuse_approved'):
            refusals.append(f"Q4: {ev['sub_clip_id']} appears twice in the master (options #{seen[ev['sub_clip_id']]} and #{ev['approved_from_option']})")
        seen[ev['sub_clip_id']] = ev['approved_from_option']
        if ev['timeline_frames'] <= 1:
            refusals.append(f"Q5: 1-frame cut in option #{ev['approved_from_option']}")
        if ev['timeline_in_frame'] != cursor:
            refusals.append(f"Q5: gap or overlap before option #{ev['approved_from_option']} at frame {cursor}")
        cursor = ev['timeline_out_frame']
    expected = sum(b['target_beat_frames'] for b in package['beats'])
    if cursor != expected:
        refusals.append(f'Q5: master runtime {cursor} frames, beats total {expected}')
    target = (package['project'] or {}).get('target_runtime_s')
    if target and abs(expected / package['timeline']['fps'] - target) > 5:
        flags.append(f"Q5: runtime {expected / package['timeline']['fps']:.1f} s differs from the brief's target {target} s")
    return {'refusals': refusals, 'flags': flags}
