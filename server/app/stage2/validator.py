"""Mechanical judge for options (2A) and master (2B): grammar G1–G17, editor rules R*, QC Q1–Q8 (design/15 §3 + design/17 §2).
Returns {'refusals': [...], 'flags': [...]}: a refusal rejects the proposal; a flag is shown to the operator."""
import re
from fractions import Fraction

from .package import SHOT_SIZES, GRID
from .slides import NOTE_KINDS

ROLL_SPEAKER = 'ELIGIBLE_A_ROLL_SPEAKER'
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


def _piece(tag, ev, row, policy, refusals, flags=None):
    """The checks every footage piece passes, a shot or an alternative: eligible, client-safe, speaker policy, match and evidence, inside its
    window (G1), its action peak (G2), its hold (G3). Returns False when its frames are unusable (the caller stops there)."""
    if not row['eligibility'].startswith('ELIGIBLE') or not row['client_safe'] or row['risk_flags']:
        refusals.append(f'{tag}: G10/Q8 sub-clip is not eligible or not client-safe ({row["eligibility"]}, risk flags {row["risk_flags"]})')
    if row['eligibility'] == ROLL_SPEAKER and not policy.get('show_speaker_video'):
        refusals.append(f'{tag}: Q1 speaker on screen while show_speaker_video is false')
    if ev.get('match') not in ('direct', 'b_roll', 'library') or not str(ev.get('evidence') or '').strip():   # design/147 L4: a library proposal
        refusals.append(f'{tag}: match (direct, b_roll or library) and evidence (the log fields that show it matches the words) are required')
    if ev.get('match') == 'library' and not row.get('library'):
        refusals.append(f'{tag}: match library is for a clip of the client\'s library (`vw options library`), not this batch')
    a, z = ev.get('source_in_frame'), ev.get('source_out_frame')
    if not (isinstance(a, int) and isinstance(z, int) and row['in_frame'] <= a < z <= row['out_frame']):
        refusals.append(f"{tag}: G1 source frames {a}-{z} must lie inside the usable window {row['in_frame']}-{row['out_frame']}")
        return False
    peak = row.get('action_peak')
    move = next((m for m in row.get('camera_moves') or [] if peak and peak['in_frame'] < m['start_frame'] <= peak['out_frame'] and z >= m['start_frame']), None)
    if peak and a <= peak['in_frame'] and peak['out_frame'] > z and move:   # design/142 R4: the action is complete where the reported camera move starts
        if flags is not None:
            flags.append(f"{tag}: G2 move: ends at {z}, before the reported {move['kind']} at {move['start_frame']}; the action is complete")
    elif peak and not (a <= peak['in_frame'] and peak['out_frame'] <= z):
        refusals.append(f"{tag}: G2 must_include_action_peak {peak['in_frame']}-{peak['out_frame']} dropped")
    if (z - a) / Fraction(row['source_fps']) < row['min_hold_s'] and not ev.get('hold_last_frame'):
        refusals.append(f"{tag}: G3 shorter than min_comprehension_hold_s {row['min_hold_s']}")
    return True


def related_as_direct(row, step_id, ev):
    """design/193 R4: with a log by sentence, a shot marked direct under a sentence needs the clip study's EXACT or PARTLY fit of that piece to
    that sentence. Only RELATED, or no fit at all: the reason it is refused, with the ways out. None when it passes, when the shot is B-roll or
    a library clip, or when the log is by paragraph (an older film is checked as before)."""
    if row.get('fit_unit') != 'sentence' or row.get('library') or ev.get('match') != 'direct':
        return None
    fit = next((f for f in row.get('sentence_fits') or [] if f.get('step_id') == step_id), None)
    if fit and fit.get('match') != 'RELATED':
        return None
    why = ('the clip study marked this piece only RELATED to this sentence' + (f" (it does not show: {fit['missing']})" if fit.get('missing') else '')) if fit \
        else 'the clip study gives this piece no fit for this sentence'
    return why + ': a direct match must show what the sentence says. Place it as B-roll (match b_roll), choose another piece, or leave a blank'


def _note(tag, ev, refusals):
    """design/127: a doubtful shot carries a note {kind, question}, shown with it; the operator's answer is the shot's own."""
    if 'decision' in ev:
        refusals.append(f'{tag}: decision is retired: a doubtful shot carries a note {{kind, question}}; B-roll is a shot with match b_roll and needs no question')
    d = ev.get('note')
    if d is None:
        return None
    if isinstance(d, dict) and d.get('kind') == 'b_roll':
        refusals.append(f'{tag}: B-roll is a shot with match b_roll; it needs no question')
        return None
    if not isinstance(d, dict) or d.get('kind') not in NOTE_KINDS or not str(d.get('question') or '').strip():
        refusals.append(f'{tag}: a note needs kind ({", ".join(NOTE_KINDS)}) and the question for the operator')
        return None
    return d


def validate_options(doc, package, policy):
    refusals, flags = [], []
    rows = {r['sub_clip_id']: r for r in package['sub_clips']}
    beats = {b['beat_id']: b for b in package['beats']}
    tl_fps = package['timeline']['fps']
    opts = doc.get('options') or []
    if doc.get('gaps'):   # design/125 P13: the declared gap is retired
        refusals.append("declare a gap is retired; write it as one blank of the scene's length")
    numbers = [o.get('option_number') for o in opts]
    if numbers != list(range(1, len(opts) + 1)):
        refusals.append('G12: option numbers must run 1..N in order')
    by_beat = {}
    for o in opts:
        by_beat.setdefault(o.get('beat_id'), []).append(o)
    for bid in beats:
        if bid not in by_beat:
            refusals.append(f"{bid}: no option; a scene with no footage is an option made of one blank of the scene's length")
    for bid, group in by_beat.items():
        if bid not in beats:
            refusals.append(f'unknown beat {bid}')
            continue
        if len(group) > 1 or any(o.get('rank') not in (None, 'PRIMARY') for o in group):   # design/127
            refusals.append(f'{bid}: a second cut of a scene is retired; give an alternative for a shot (`alternatives` on the shot: another clip, the same length)')
    words = {w['id']: w for w in (package.get('narration') or {}).get('words') or []}
    silences = (package.get('narration') or {}).get('silences') or []
    uses = {}    # clip_id -> [(option_number, beat_id, event_index, has_reuse_note, source in, source out)] in film order (design/21 rule 7)
    alts = []    # design/127: (option_number, event_index, alternative number, clip_id)
    direct, b_rolls = {}, []   # design/127: B-roll comes after the exact matches
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
                if ev.get('alternatives'):
                    refusals.append(f'{tag}: an AI shot has no clip to replace: alternatives go on a footage shot')
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
            # design/21: every real shot states how it matches the words; design/127: a doubtful one carries a note, B-roll needs none
            d = _note(tag, ev, refusals)
            if row.get('grade') == 'C' and not (d and d.get('kind') == 'poor_quality'):
                refusals.append(f'{tag}: E3 the log grades this sub-clip C (poor quality): give it a note (kind poor_quality) or leave a blank')
            uses.setdefault(row['clip_id'], []).append((n, bid, i, bool(d and d.get('kind') == 'reuse'), ev.get('source_in_frame'), ev.get('source_out_frame')))
            if ev.get('match') == 'b_roll':
                b_rolls.append((n, i, row['clip_id']))
            else:
                direct.setdefault(row['clip_id'], n)
            if not _piece(tag, ev, row, policy, refusals, flags):
                continue
            a, z = ev['source_in_frame'], ev['source_out_frame']
            src_fps = Fraction(row['source_fps'])
            hold_s = row['min_hold_s'] + (1.0 if row['effective_shot_size'] in ('WS', 'EWS') else 0.0) - (0.5 if row['effective_shot_size'] in ('CU', 'ECU') else 0.0)
            hold_s = max(hold_s, row['min_hold_s'])
            if row['min_hold_s'] <= (z - a) / src_fps < hold_s:
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
            if natural_cut_missed(a, row['natural_cut_frames'], Fraction(row['source_fps']) / Fraction(str(tl_fps))) and a != row['in_frame']:   # design/142 R5
                flags.append(f'{tag}: R1 a natural cut point was within reach of the in-point and was not used')
            if row['accent_frames'] and all(f > z or f < a for f in row['accent_frames']):
                flags.append(f'{tag}: R1 no accent event inside the shot')
            n_tl, ratio = _tl_frames(ev, row, tl_fps)
            ev['_timeline_frames'] = n_tl
            ev['_fps_ratio'] = str(ratio)
            for m, alt in enumerate(ev.get('alternatives') or [], 1):   # design/127: another clip for the same words, the same length
                atag = f'{tag} alternative {m}'
                arow = rows.get(alt.get('sub_clip_id')) if isinstance(alt, dict) else None
                if not arow:
                    refusals.append(f'{atag}: unknown sub-clip')
                    continue
                alts.append((n, i, m, arow['clip_id']))
                if _piece(atag, alt, arow, policy, refusals, flags) and _tl_frames(alt, arow, tl_fps)[0] != n_tl:
                    refusals.append(f"{atag}: an alternative fills its shot's time exactly: {n_tl} frames (it has {_tl_frames(alt, arow, tl_fps)[0]})")
            total += n_tl
            if prev:
                ps, cs = prev['effective_shot_size'], row['effective_shot_size']
                if ps in SHOT_SIZES and cs in SHOT_SIZES and ps == cs:
                    sizes.append(cs)
                    flags.append(f'{tag}: G5 adjacent shots of the same size ({cs})')
                    if prev['clip_id'] == row['clip_id']:   # design/125 O7: two parts of one clip side by side at one size is a jump cut
                        refusals.append(f'{tag}: G5 two parts of clip {row["clip_id"]} side by side at the same size ({cs}): put another shot between them or change the size')
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
                if prev['color_group'] and row['color_group'] and prev['color_group'] != row['color_group']:   # design/142 R5: an unknown look never trips it
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
                    said = str((ev.get('marker_reasons') or {}).get('action') or '').strip()   # design/142 R4: the whole action and the pre-roll come first; a reason makes it information
                    flags.append(f"{tag}: B2 answered: the word {words[awid]['text']!r} is not within 6 frames of the action accent ({said})" if said else
                                 f"{tag}: B2 the word {words[awid]['text']!r} is not within 6 frames of the shot's action accent")
            if i > 0 and not row['nat_sound'] and any(s['start_frame'] < cursor < s['end_frame'] for s in silences):
                flags.append(f'{tag}: B3 cuts inside a narration pause of 1.2 s or more; hold the shot or use a sub-clip with clean natural sound')
            cursor += n_tl
            prev = row
        # design/91 N17: every step the scene narrates is shown by one event, or left as a blank for visuals
        own_steps = {s['step_id']: s for s in beat.get('steps') or []}
        smap = o.get('steps')
        if smap is None:
            if own_steps:
                flags.append(f'OPTION #{n}: N17 no step map: name the event that shows each step of the scene ({", ".join(own_steps)})')
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
                said = related_as_direct(row, sid, e)
                if said:
                    refusals.append(f'OPTION #{n}: step {sid} ({own_steps[sid]["text"][:60]}) is shown by shot {k} as a direct match, but {said}')
                if row.get('process_stage') and beat.get('process_stages') and row['process_stage'] not in beat['process_stages']:
                    flags.append(f"OPTION #{n}: N17 stage: step {sid} ({own_steps[sid]['text'][:60]}) is shown by a clip of the stage {row['process_stage']!r}; the scene narrates "
                                 f"{', '.join(beat['process_stages'])}: the right step?")   # design/126 OP3: for information, its reason already required
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
                if carry_flag(kept, e, lm):
                    flags.append(f"OPTION #{n}: N14 shot {k} ({e.get('sub_clip_id')}) does not show {kept!r}, which the step before left (its log lists {', '.join(map(str, lm)) or 'nothing'})")
        if total != beat['target_beat_frames']:
            refusals.append(f"OPTION #{n}: G11 timeline length {total} frames must equal the beat's {beat['target_beat_frames']}")
        for i, ev in enumerate(events):
            ev.pop('_lm', None)
    # design/21 rule 7: a clip appears once in the film. Its first and backup options for one scene may share it (only one is kept);
    # design/125 O7: a later part of the same clip in the same cut, not overlapping the earlier one, is not a reuse (G5 still flags two of one size
    # side by side). Any other second use, including a part of the same clip in another scene, must be a decision of kind reuse.
    for cid, us in uses.items():
        for j, (n, bid, i, is_reuse, a, _z) in enumerate(us):
            earlier = [u for u in us[:j] if not (u[1] == bid and u[0] != n) and not (u[0] == n and isinstance(a, int) and isinstance(u[5], int) and u[5] <= a)]
            if earlier and not is_reuse:
                refusals.append(f'OPTION #{n} shot {i + 1}: Q4 clip {cid} is already used (option #{earlier[0][0]}); a second use, even of another part, needs a note of kind reuse or another clip')
    seen_alt = set()
    for n, i, m, cid in alts:   # design/127: an alternative's clip is used nowhere else in the cut
        if cid in uses or cid in seen_alt:
            refusals.append(f'OPTION #{n} shot {i + 1}: alternative {m} uses clip {cid}, which is already in the cut: give a clip used nowhere else')
        seen_alt.add(cid)
    for n, i, cid in b_rolls:   # design/127: B-roll is placed after the exact matches, from the clips they left unused
        if cid in direct:
            refusals.append(f'OPTION #{n} shot {i + 1}: B-roll comes after the exact matches: clip {cid} is a direct match in option #{direct[cid]}; take B-roll from a clip no exact match uses')
    # design/91 N14: consecutive scenes narrating the same process stage stay in one place unless the option names the move
    order = [b for b in package['beats'] if by_beat.get(b['beat_id'])]
    for a, b in zip(order, order[1:]):
        if not set(a.get('process_stages') or []) & set(b.get('process_stages') or []):
            continue
        oa, ob = by_beat[a['beat_id']][0], by_beat[b['beat_id']][0]
        last = next((rows.get(e.get('sub_clip_id')) for e in reversed(oa.get('events') or []) if not e.get('blank') and e.get('sub_clip_id') in rows), None)
        first = next((rows.get(e.get('sub_clip_id')) for e in ob.get('events') or [] if not e.get('blank') and e.get('sub_clip_id') in rows), None)
        if last and first and last.get('color_group') and first.get('color_group') and last.get('color_group') != first.get('color_group') and not str(ob.get('moves_place') or '').strip():
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


RULE_RE = re.compile(r'(?:^|: )(rule 11|N17 stage|B2 answered|G2 move|[A-Z]\d{1,2})(?=[ :])')   # design/142 R4: an answered B2 and a cut before a camera move   # design/126 OP3: N17's chapter flag is its own kind


def _words(text):
    return ' '.join(re.split(r'[\s_\-]+', str(text).lower())).strip()


def carried(kept, labels):
    """design/142 R3: a carry-over entry is in a clip's landmark labels when either holds the other, spaces, underscores and hyphens counting as one."""
    return all(any(_words(k) in _words(x) or _words(x) in _words(k) for x in labels) for k in kept)


def carry_flag(kept, ev, labels):
    """N14 is answered by the words, or by the assistant's reason that a label is the same thing under another name (carries_over_seen)."""
    return not ev.get('blank') and not carried([kept], labels) and not str(ev.get('carries_over_seen') or '').strip()


def natural_cut_missed(a, natural, ratio):
    """design/142 R5 (SK, design/140 Q4): R1 fires only when a natural cut point lay within B1's six-frame window of the in-point (in source frames:
    six timeline frames times source fps over timeline fps) and the shot did not start on it."""
    reach = 6 * ratio
    return any(0 < abs(a - f) <= reach for f in natural or [])


WHY_KINDS = ('wrong action', 'wrong object', 'already used', 'claim or number', 'too short', 'unusable crop', 'contradicts the words', 'other')   # design/142 R2


def cut_reasons(doc, rows):
    """design/142 R2: the cut carries its own reasons. A blank names the clips considered with why each was turned down, or none_fit; a shot with
    alternatives says preferred_because. rows: {sub_clip_id: row}. Returns refusals; run on every new proposal (a cut proposed before keeps its form)."""
    out = []
    for o in (doc or {}).get('options') or []:
        for i, ev in enumerate(o.get('events') or [], 1):
            tag = f"OPTION #{o.get('option_number')} event {i}"
            if ev.get('blank'):
                considered, none_fit = ev.get('considered') or [], str(ev.get('none_fit') or '').strip()
                if not considered and not none_fit:
                    out.append(f'{tag}: a blank names the clips considered (considered: [{{sub_clip_id, why}}]) or says none_fit with one line: which clips were looked at, and why each did not fit')
                for c in considered:
                    if not isinstance(c, dict) or c.get('sub_clip_id') not in rows:
                        out.append(f"{tag}: considered names an unknown sub-clip {(c or {}).get('sub_clip_id') if isinstance(c, dict) else c!r}")
                    elif c.get('why') not in WHY_KINDS:
                        out.append(f"{tag}: considered {c['sub_clip_id']}: why is one of {', '.join(WHY_KINDS)}")
                    elif c['why'] == 'other' and not str(c.get('words') or '').strip():
                        out.append(f"{tag}: considered {c['sub_clip_id']}: why other needs its words")
            else:
                if ev.get('alternatives') and not str(ev.get('preferred_because') or '').strip():
                    out.append(f"{tag} ({ev.get('sub_clip_id')}): a shot with alternatives says why it was preferred (preferred_because)")
                said = ev.get('marker_reasons') if isinstance(ev.get('marker_reasons'), dict) else {}
                for field, key in (('illustrates_word_id', 'illustrates'), ('action_word_id', 'action')):   # design/142 R4 (SK, design/140 Q2)
                    if not ev.get(field) and not str(said.get(key) or '').strip():
                        out.append(f"{tag} ({ev.get('sub_clip_id')}): name {field}, or say why it cannot be met in marker_reasons.{key} (shown to the operator)")
    return out


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


INFO_KINDS = ('R1', 'R4', 'R8', 'R10', 'N17 stage', 'B2 answered', 'G2 move')   # design/125 P11: information only when shots are cut to the meaning across clips; design/126 OP3


def answer_flags(flags):
    """design/125 P11: the check's answer to the assistant: the flags to act on in full, the information-only kinds as one line of counts."""
    info = [g for g in group_flags(flags) if g['rule'] in INFO_KINDS]
    total = sum(g['count'] for g in info)
    return {'act_on': [f for f in flags if (RULE_RE.search(f) or [None, 'other'])[1] not in INFO_KINDS],
            'for_information': f"{total} for information: " + ', '.join(f"{g['rule']} {g['count']}" for g in info) + '; the full list is in `vw options status`' if info else ''}   # design/142 R10


def validate_master(master, package):
    """Q4 zero duplicate sub-clips (design/125 O7: a later, non-overlapping part of one sub-clip in the same scene is not one); Q5 runtime equals the
    sum of beats with no gaps or 1-frame cuts; events ripple from zero."""
    refusals, flags = [], []
    seen = {}
    cursor = 0
    for ev in master['events']:
        if ev.get('kind') == 'gap':
            cursor += ev['timeline_frames']
            continue
        prev = seen.get(ev['sub_clip_id'])
        if prev and not ev.get('reuse_approved') and not (prev[1] and prev[1] == ev.get('beat_id') and isinstance(prev[2], int) and prev[2] <= (ev.get('source_in_frame') or 0)):
            refusals.append(f"Q4: {ev['sub_clip_id']} appears twice in the master (options #{prev[0]} and #{ev['approved_from_option']})")
        seen[ev['sub_clip_id']] = (ev['approved_from_option'], ev.get('beat_id'), ev.get('source_out_frame'))
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
