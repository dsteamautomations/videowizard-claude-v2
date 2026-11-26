"""The options package: beats with timeline windows (narration stays one continuous file; windows follow its natural gaps, design/17 C1),
summary cards, the eligible sub-clip table derived from the clip logs and the Stage 1.5 solver, learned client rules."""
import math
import re
from collections import Counter
from difflib import SequenceMatcher, get_close_matches
from fractions import Fraction

from .review import SHORT

SHOT_SIZES = ['EWS', 'WS', 'MWS', 'MS', 'MCU', 'CU', 'ECU']
GRID = ['Top_Left', 'Top_Center', 'Top_Right', 'Mid_Left', 'Mid_Center', 'Mid_Right', 'Bottom_Left', 'Bottom_Center', 'Bottom_Right']


def frames_of(seconds, fps):
    return int(round(Fraction(str(seconds)) * Fraction(str(fps))))


def beat_windows(script_beats, timing, timeline_fps, audio_duration_s):
    """Beat i runs from its first word's start to beat i+1's first word's start (last: to the end of the recording). Frames at timeline fps."""
    words = timing['words']
    starts = []
    for b in script_beats:
        own = [w for w in words if w['passage_id'] == b['passage_id']]
        if not own:
            raise ValueError(f"narration timing has no words for {b['beat_id']}")
        starts.append((b, own[0]['start_s'], own[-1]['end_s']))
    out = []
    for i, (b, first, last) in enumerate(starts):
        start_s = 0.0 if i == 0 else first
        end_s = starts[i + 1][1] if i + 1 < len(starts) else float(audio_duration_s)
        a, z = frames_of(start_s, timeline_fps), frames_of(end_s, timeline_fps)
        if z <= a:
            raise ValueError(f"{b['beat_id']} has no timeline length")
        out.append({'beat_id': b['beat_id'], 'passage_id': b['passage_id'], 'text': b['text'], 'timeline_start_frame': a, 'timeline_end_frame': z,
                    'target_beat_frames': z - a, 'narration_first_word_s': first, 'narration_last_word_s': last, 'window_start_s': start_s, 'window_end_s': end_s})
    return out


def lighting_class(text):
    t = (text or '').lower()
    if 'hard' in t and 'sun' in t:
        return 'HARD_SUN'
    if 'overcast' in t or 'soft' in t:
        return 'SOFT_OVERCAST'
    if 'interior' in t or 'mixed' in t:
        return 'MIXED_INTERIOR'
    return 'UNCLASSIFIED'


def confidence_of(sub):
    """R14: uncertainty is a cost. 1.0 when every uncertainty field is empty and tc_confidence HIGH; lower otherwise."""
    score = 1.0
    if sub.get('tc_confidence') == 'MEDIUM':
        score -= 0.2
    if sub.get('tc_confidence') == 'NEEDS_BOUNDARY_CHECK':
        score -= 0.5
    for text in (sub.get('visual_action_uncertainty'), sub.get('sub_clip_uncertainty'), (sub.get('people_and_speaker_analysis') or {}).get('uncertainty'),
                 (sub.get('camera_and_optics') or {}).get('uncertainty'), (sub.get('continuity_and_story') or {}).get('beat_fit_limits')):
        if str(text or '').strip():
            score -= 0.08
    return round(max(0.0, score), 2)


FRAME_BASE = ('design/142 R10: source frames (in_frame, out_frame, source_in_frame, source_out_frame, the action peak, accent and natural cut frames) count '
              "at the clip's own rate (source_fps); timeline frames count at the film's rate (timeline.fps); in_s and out_s give a piece's seconds in its clip.")
SCENES_SHAPE = {'contract': 'vw2-scenes-v1',   # design/142 R8: the shape of out/scenes.json (Revathi's point 1)
                'scenes': [{'first_word_id': 'the id of the word the scene starts at (a sentence start)', 'title': 'a few plain words',
                            'process_stages': ['every chapter of the brief this scene covers; empty for an opening, a closing or a title'],
                            'why': 'why this paragraph was split, or kept together although it covers two chapters (shown to the operator)'}],
                'pauses': [{'after_word_id': 'the last word of a sentence', 'seconds': 1.0, 'reason': 'why the picture needs the breath'}],
                'dropped_chapters': [{'chapter': 'a chapter of the brief no scene carries', 'words': "the operator's words dropping it"}],
                'chapter_map': {'a chapter name the clip studies carry that is not a chapter of this film (listed under chapters_unknown; leave chapter_map out when there is none)':
                                'the chapter of this film that shows the same thing, letter for letter, or "" when none does'}}


def camera_moves(sub, src_fps):
    """design/142 R4: the camera moves the analysis reported apart from the action, in source frames."""
    return [{'start_frame': int(round(Fraction(str(m['start_s'])) * src_fps)), 'end_frame': int(round(Fraction(str(m['end_s'])) * src_fps)), 'kind': m.get('kind') or 'other'}
            for m in sub.get('camera_moves') or [] if isinstance(m, dict) and m.get('start_s') is not None and m.get('end_s') is not None]


def ruled_out(rows):
    """design/142 R2: the sub-clips the analysis ruled out, with its reason, so the first cut can say why they were never candidates."""
    return [{'sub_clip_id': r['sub_clip_id'], 'clip': r.get('clip_name'), 'eligibility': r['eligibility'], 'reason': r.get('ruled_out_reason') or r['eligibility'].replace('_', ' ').lower()}
            for r in rows if not str(r['eligibility']).startswith('ELIGIBLE')]


FIT_LINE = re.compile(r'BEAT_(\d+)\D{0,6}?(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*s?\W{0,4}(EXACT|PARTLY|RELATED)\W*(.*)', re.S)


def _beat_lines(text):
    """A fit field cut into its lines, one per sentence named: each starts at a beat id."""
    return [p.strip(' \n;/|-') for p in re.split(r'(?=BEAT_\d+)', str(text or '')) if p.strip().startswith('BEAT_')]


def own_lines(sub, n_sentences):
    """design/193 R3: a piece's own lines for the placer: what it shows, and (from a log by sentence) its fit to each sentence, read from the two
    text fields the clip study writes: the sentence's number, the seconds, EXACT, PARTLY or RELATED, why, and what is missing. A line that is not
    in the form asked for, names a sentence the script does not have, or gives seconds outside the piece is left out and counted. A sentence the
    study lists as primary with no usable line still counts, as exact, with "no line given". n_sentences 0: a log by paragraph, nothing is read."""
    out = {'what': sub.get('visual_action_observed')}
    if not n_sentences:
        return out
    story, w = sub.get('continuity_and_story') or {}, sub.get('max_usable_window') or {}
    lo, hi = float(w.get('in_s') or 0) - 0.35, float(w.get('out_s') or 0) + 0.35
    number = lambda t: int(re.match(r'BEAT_(\d+)', t).group(1))
    missing = {number(l): re.sub(r'^BEAT_\d+\W*', '', l).strip() for l in _beat_lines(story.get('beat_fit_limits'))}
    fits, unread = [], 0
    for line in _beat_lines(story.get('beat_fit_reasoning')):
        m = FIT_LINE.match(line)
        if not m:
            unread += 1
            continue
        i, a, z = int(m.group(1)), float(m.group(2)), float(m.group(3))
        if not 1 <= i <= n_sentences or a < lo or z > hi or a >= z:
            unread += 1
            continue
        if not any(f['sentence'] == i for f in fits):
            fits.append({'sentence': i, 'from_s': a, 'to_s': z, 'match': m.group(4), 'why': ' '.join(m.group(5).split())[:400], 'missing': missing.get(i, '')})
    for b in story.get('primary_fit_for_beats') or []:
        m = re.match(r'BEAT_(\d+)$', str(b))
        if m and 1 <= int(m.group(1)) <= n_sentences and not any(f['sentence'] == int(m.group(1)) for f in fits):
            fits.append({'sentence': int(m.group(1)), 'from_s': None, 'to_s': None, 'match': 'EXACT', 'why': 'no line given', 'missing': missing.get(int(m.group(1)), '')})
    return {**out, 'sentence_fits': fits, 'fit_lines_unread': unread}


def fit_unit(identities):
    """design/193: which kind of log a film holds, and why when it is not by sentence. By sentence when every clip was studied so; else by
    paragraph, as before, with the reason for the tool's answer ('' for an older film). SK, 23 Nov 2026 (VW-25): a count of sentences that
    differs from the narration's no longer packages the whole film by paragraph; the sentences are paired by their words (`pair_sentences`)."""
    kinds = [i.get('fit_unit') == 'sentence' for i in identities]
    if not any(kinds):
        return 'paragraph', ''
    if not all(kinds):
        return 'paragraph', 'Some clips were studied before the fit by sentence: this film is packaged by paragraph, as before.'
    return 'sentence', ''


def study_sentences(identity, n_script):
    """How many sentences a clip's study numbered, when it numbered this film's script; 0 (its line fits are not read) for a study by paragraph
    or one made against another count of sentences."""
    n = int(identity.get('sentences') or 0) if identity.get('fit_unit') == 'sentence' else 0
    return n if n == n_script else 0


def chapter_map_of(document, chapters):
    """SK, 23 Nov 2026 (VW-25): the scenes file's `chapter_map`, checked: a chapter name of the clip studies → a chapter of this film, or '' for
    none. A clip study reused from another film carries that film's chapter names; without the map its pieces fit no scene by chapter."""
    cmap = document.get('chapter_map') or {}
    if not isinstance(cmap, dict):
        raise ValueError('chapter_map is an object: each chapter name of the clip studies that is not a chapter of this film, with the chapter of this film that shows the same thing, or "" for none.')
    for old, new in cmap.items():
        if new not in ('', None) and new not in chapters:
            raise ValueError(f"chapter_map: {old!r} is given {new!r}, which is not a chapter of the brief ({', '.join(chapters) or 'the brief names none'}).")
    return {str(old): new or '' for old, new in cmap.items()}


def apply_chapter_map(rows, chapters, cmap):
    """Gives every piece whose chapter is not one of this film's the chapter the map names (its own name is kept as process_stage_study; '' in
    the map: no chapter), and returns the names the map does not hold, most pieces first, each with the nearest chapter of this film as a hint.
    Nothing is guessed: a name not in the map stays as it is. A film whose brief names no chapters has nothing to map to."""
    if not chapters:
        return []
    left = Counter()
    for r in rows:
        own = r.get('process_stage')
        if not own or own in chapters:
            continue
        if own in cmap:
            r['process_stage_study'], r['process_stage'] = own, cmap[own] or None
        else:
            left[own] += 1
    return [{'name': n, 'pieces': k, 'nearest': (get_close_matches(n, chapters, 1, 0.5) or [''])[0]} for n, k in left.most_common()]


def pair_sentences(script, narration):
    """SK, 23 Nov 2026 (VW-25): {script sentence number: narration sentence number}, paired by their words. The clip study numbers the script's
    sentences; the narration may count them differently (a title line read into the first sentence, one sentence read as two). A script sentence
    goes to the narration sentence that holds most of its words, the earlier one on a tie; one with fewer than half its words found has no pair."""
    words = lambda texts: [(n, w) for n, t in enumerate(texts, 1) for w in re.findall(r'\w+', str(t or '').lower())]
    a, b = words(script), words(narration)
    found = {}
    for x, y, size in SequenceMatcher(None, [w for _, w in a], [w for _, w in b], autojunk=False).get_matching_blocks():
        for k in range(size):
            found.setdefault(a[x + k][0], Counter())[b[y + k][0]] += 1
    total = Counter(n for n, _ in a)
    return {n: hits.most_common(1)[0][0] for n, hits in sorted(found.items()) if sum(hits.values()) * 2 >= total[n]}


def pairing_note(script, n_narration, pair, fits, other_count):
    """What prepare tells the assistant about the pairing; '' when the counts agree and nothing was lost. fits: every line fit read from the
    studies (its `sentence` is the script's number); other_count: the names of the clips studied against another count of sentences."""
    out = []
    lost = [n for n in range(1, len(script) + 1) if n not in pair]
    if len(script) != n_narration or lost:
        out.append(f'The script has {len(script)} sentences and the narration has {n_narration}: they were paired by their words'
                   + (', and every script sentence was found.' if not lost else '.'))
    for n in lost:
        k = sum(1 for f in fits if f['sentence'] == n)
        out.append(f"No narration sentence was found for script sentence {n} ('{' '.join(str(script[n - 1]).split())[:80]}'): {k} line fit{'s are' if k != 1 else ' is'} not used.")
    if other_count:
        out.append(f"{len(other_count)} clip{'s were' if len(other_count) != 1 else ' was'} studied against another count of sentences ({', '.join(other_count[:12])}"
                   f"{', ...' if len(other_count) > 12 else ''}): their line fits are not used, they fit by chapter only.")
    return ' '.join(out)


def scene_fits_by_sentence(rows, windows, sentences, pair=None):
    """design/193 R3: with logs by sentence, a row fits a scene directly when the clip study marked it EXACT or PARTLY for a sentence of that scene,
    is related when only RELATED, and fits by chapter when its process_stage is the scene's chapter (as `scene_fits`). A sentence belongs to the scene
    its first word starts in, and is numbered there as the scene's step (BEAT_03.S2), as `with_steps` numbers it. Each fit gains its scene and step.
    pair (`pair_sentences`): the study's sentence number → the narration's; a fit whose sentence has no pair is left out, and a kept fit carries
    the narration's number. None: number for number, as before."""
    place = {}
    for w in windows:
        own = [i for i, s in enumerate(sentences or [], 1) if w['timeline_start_frame'] <= s['start_frame'] < w['timeline_end_frame']]
        place.update({i: (w['beat_id'], f"{w['beat_id']}.S{n}") for n, i in enumerate(own, 1)})
    for r in rows:
        r['model_fits'] = {'primary': r['primary_fits'], 'secondary': r['secondary_fits']}
        kinds, fits = {}, []
        for f in r.get('sentence_fits') or []:
            spoken = f['sentence'] if pair is None else pair.get(f['sentence'])
            at = place.get(spoken)
            if not at:
                continue
            fits.append({**f, 'sentence': spoken, 'scene': at[0], 'step_id': at[1]})
            if kinds.get(at[0]) != 'direct':
                kinds[at[0]] = 'related' if f['match'] == 'RELATED' else 'direct'
        for w in windows:
            if kinds.get(w['beat_id']) != 'direct' and r.get('process_stage') and r['process_stage'] in w['process_stages']:
                kinds[w['beat_id']] = 'chapter'
        kinds = {w['beat_id']: kinds[w['beat_id']] for w in windows if w['beat_id'] in kinds}
        r['sentence_fits'] = fits
        r['primary_fits'] = [b for b, k in kinds.items() if k != 'related']
        r['secondary_fits'] = [b for b, k in kinds.items() if k == 'related']
        r['fit_kinds'], r['fit_source'], r['fit_unit'] = kinds, 'clip study by sentence, and scene chapter', 'sentence'
    return rows


def sub_clip_row(clip, log, sub, timeline_fps, n_sentences=0):
    src_fps = Fraction(str(clip.get('fps') or timeline_fps))
    w = sub['max_usable_window']
    st = sub['stage15']
    cam, pace, story, people = sub['camera_and_optics'], sub['pacing_and_flow'], sub['continuity_and_story'], sub['people_and_speaker_analysis']
    peak = sub.get('must_include_action_peak')
    crop = (st.get('crop_solution') or {}) if st['visual_eligibility'] == 'ELIGIBLE_WITH_CROP' else {}
    return {'sub_clip_id': f"{clip['id']}:{sub['sub_clip_id']}", 'log_sub_clip_id': sub['sub_clip_id'], 'clip_id': clip['id'], 'clip_name': clip['name'], 'source_fps': str(src_fps), 'source_width': clip.get('width'), 'source_height': clip.get('height'),
            'in_frame': w['in_frame'], 'out_frame': w['out_frame'], 'in_s': round(float(Fraction(w['in_frame']) / src_fps), 3), 'out_s': round(float(Fraction(w['out_frame']) / src_fps), 3), 'duration_s': w['duration_s'],
            'handles': {k: w[k] for k in ('video_handle_frames_before', 'video_handle_frames_after')},
            'grade': sub['usability_grade'], 'shot_role': sub['shot_role'], 'client_safe': st.get('client_safe_effective', sub['client_safe']),
            'risk_flags': st.get('risk_flags_effective', sub.get('risk_flags') or []), 'risk_flags_waived': st.get('risk_flags_waived') or [],
            'native_shot_size': cam['native_shot_size'], 'effective_shot_size': st.get('effective_post_crop_shot_size') or cam['native_shot_size'],
            'camera_moves': camera_moves(sub, src_fps), 'eligibility': st['visual_eligibility'], 'ruled_out_reason': (st.get('crop_solution') or {}).get('reason'), 'crop_rect': crop.get('crop_rect'), 'zoom': crop.get('zoom_x'), 'position': [crop.get('position_x'), crop.get('position_y')] if crop else None,
            'ui_path': st.get('ui_path'), 'still_eligible': st.get('still_frame_dynamic_zoom_eligible'),
            'entry_eye_grid': pace['entry_eye_grid'], 'exit_eye_grid': pace['exit_eye_grid'], 'screen_direction': cam['subject_screen_direction'],
            'lighting': lighting_class(log.get('lighting_and_weather')), 'color_group': log.get('color_match_group_id'), 'energy': pace['kinetic_energy_score'],
            'min_hold_s': pace['min_comprehension_hold_s'], 'action_peak': {'in_frame': frames_of(peak['in_s'], src_fps), 'out_frame': frames_of(peak['out_s'], src_fps)} if peak else None,
            'pairing_constraints': sub.get('pairing_constraints') or [],
            'natural_cut_frames': sorted({e.get('frame') if isinstance(e.get('frame'), int) else frames_of(e['s'], src_fps) for e in pace.get('natural_cut_points') or []}),
            'accent_frames': sorted({e.get('frame') if isinstance(e.get('frame'), int) else frames_of(e['s'], src_fps) for e in pace.get('accent_events') or []}),
            'primary_fits': story.get('primary_fit_for_beats') or [], 'secondary_fits': story.get('secondary_fit_for_beats') or [], 'beat_fit_basis': story.get('beat_fit_basis'),
            'beat_fit_limits': story.get('beat_fit_limits'), 'landmarks': story.get('world_landmarks_and_props') or [], 'process_stage': story.get('process_stage'),
            'outcome_state': story.get('outcome_state'), 'action_completeness': sub.get('action_completeness'),
            'nat_sound': [{'in_frame': frames_of(i['in_s'], src_fps), 'out_frame': frames_of(i['out_s'], src_fps), 'description': i.get('description', '')} for i in sub['audio_and_sfx_plan'].get('clean_nat_sound_intervals') or []],
            'sfx_cues': sub['audio_and_sfx_plan'].get('creative_sfx_cues') or [],
            'speech': bool(people.get('speech_translation_block')), 'facts_match_visual': any(f.get('matches_visual_on_screen') for f in ((people.get('speech_translation_block') or {}).get('extracted_domain_facts') or [])),
            'tc_confidence': sub.get('tc_confidence'), 'confidence': confidence_of(sub), 'stabilization_needed': bool((sub.get('technical_qc_and_remediation') or {}).get('stabilization_needed')),
            'horizon_rotation_deg': (sub.get('technical_qc_and_remediation') or {}).get('horizon_rotation_deg') or 0.0,
            'editorial_ideas': sub.get('editorial_ideas') or [], **own_lines(sub, n_sentences)}   # design/193 R3


def scene_fits(rows, windows, paragraphs):
    """design/125 P8: after the scenes are approved, a row fits a scene directly when the clip study put it in primary for a paragraph whose words
    fall inside that scene, related when in secondary, and by chapter when its process_stage is the scene's chapter. paragraphs: the script beat id
    (the clip study's beat) → (first frame, last frame) of its words on the timeline. primary_fits = direct ∪ chapter (what consumers read),
    secondary_fits = related; fit_kinds names the kind per scene; the clip study's own lists stay in model_fits."""
    over = {p: [w['beat_id'] for w in windows if w['timeline_start_frame'] < z and a < w['timeline_end_frame']] for p, (a, z) in paragraphs.items()}
    for r in rows:
        r['model_fits'] = {'primary': r['primary_fits'], 'secondary': r['secondary_fits']}
        direct = {b for p in r['primary_fits'] for b in over.get(p, [])}
        related = {b for p in r['secondary_fits'] for b in over.get(p, [])}
        chapter = {w['beat_id'] for w in windows if r.get('process_stage') and r['process_stage'] in w['process_stages']}
        kinds = {}
        for w in windows:
            b = w['beat_id']
            kind = 'direct' if b in direct else 'chapter' if b in chapter else 'related' if b in related else None
            if kind:
                kinds[b] = kind
        r['primary_fits'] = [b for b, k in kinds.items() if k != 'related']
        r['secondary_fits'] = [b for b, k in kinds.items() if k == 'related']
        r['fit_kinds'] = kinds
        r['fit_source'] = 'clip study by paragraph, and scene chapter'
    return rows


def coverage(beats, rows, policy):
    """Blueprint §3 step 1.3 + design/17: counts per beat by primary/secondary fit and grade, uncoverable beats, low-confidence primaries, alerts."""
    report = []
    for b in beats:
        prim = [r for r in rows if b['beat_id'] in r['primary_fits'] and r['eligibility'].startswith('ELIGIBLE')]
        sec = [r for r in rows if b['beat_id'] in r['secondary_fits'] and r['eligibility'].startswith('ELIGIBLE')]
        window_s = b['target_beat_frames'] / 25.0
        holds = [r['min_hold_s'] for r in prim + sec]
        entry = {'beat_id': b['beat_id'], 'target_beat_frames': b['target_beat_frames'],
                 'primary': {g: sum(1 for r in prim if r['grade'] == g) for g in ('A', 'B', 'C')}, 'secondary': {g: sum(1 for r in sec if r['grade'] == g) for g in ('A', 'B', 'C')},
                 'candidates': [r['sub_clip_id'] for r in prim] + [r['sub_clip_id'] for r in sec if r not in prim],
                 'low_confidence': [r['sub_clip_id'] for r in prim if r['confidence'] < 0.6], 'alerts': [],
                 'kinds': {k: sum(1 for r in rows if r['eligibility'].startswith('ELIGIBLE') and _kind(r, b['beat_id']) == k) for k in ('direct', 'related', 'chapter')}}   # design/125 P8
        if not prim and not sec:
            entry['alerts'].append('ZERO COVERAGE: no eligible sub-clip fits this beat' + (' (Mode 1: stay on A-roll is possible)' if policy.get('show_speaker_video') else '; same-stage detail shot or a visuals gap'))
        if holds and min(holds) > window_s:
            entry['alerts'].append(f'UNCOVERABLE: every candidate needs at least {min(holds)} s but the beat is {window_s:.2f} s')
        report.append(entry)
    return report


def _kind(r, bid):
    """How a row fits a scene: its fit_kinds after the scenes are approved; before, the clip study's own primary (direct) or secondary (related)."""
    return (r.get('fit_kinds') or {}).get(bid) or ('direct' if bid in (r.get('primary_fits') or ()) else 'related' if bid in (r.get('secondary_fits') or ()) else None)


RANK_KINDS = ('exact', 'partly', 'related', 'chapter', 'b-roll')
GRADES = {'A': 0, 'B': 1, 'C': 2}
BROLL_LIST = 12   # how many pieces of another chapter a scene is offered as B-roll
COMMON_WORDS = set('that this with from they have been were will when what which their there about these those into then than them also each more most some such very '
                   'over under while where after before between through other only'.split())


def rank_kind(r, beat_id):
    """A piece's kind of fit to a scene, as the ranking names it. A direct fit with no sentence marks (a film packaged by paragraph) is exact."""
    kind = _kind(r, beat_id)
    if kind == 'direct':
        marks = {f.get('match') for f in r.get('sentence_fits') or [] if f.get('scene') == beat_id}
        return 'exact' if 'EXACT' in marks or not marks else 'partly'
    return kind if kind in ('related', 'chapter') else 'b-roll'


def ranked(rows, beat, used=(), broll=BROLL_LIST):
    """SK, 23 Nov 2026 (VW-25, plan Phase 3): the allowed pieces for one scene, best first, by fixed rules (no model): the kind of fit (exact for
    a sentence, partly, related, the scene's chapter, B-roll from another chapter); inside a kind, the best piece of each clip before a second
    piece of any clip; grade A, B, C; no warning before warned; a piece already in the cut (`used`) last. B-roll from another chapter is offered
    only when its description shares a word with the scene's sentences, most shared words first, `broll` pieces at most.
    The assistant's files, the review page's other clips and the ledger read this one order."""
    words = lambda text: set(re.findall(r'[^\W\d_]{4,}', str(text or '').lower())) - COMMON_WORDS
    said = words(' '.join(str(s.get('text') or '') for s in beat.get('steps') or []))
    pool = []
    for n, r in enumerate(rows):
        if not str(r.get('eligibility')).startswith('ELIGIBLE'):
            continue
        kind = RANK_KINDS.index(rank_kind(r, beat['beat_id']))
        shared = len(said & words(r.get('what'))) if kind == 4 else 0   # ponytail: shared words stand in for "shows what the words are about"; a narration in another language than the descriptions shares none, so no B-roll is offered. Upgrade: a text fit by a model, if the B-roll offered is poor
        if kind == 4 and not shared:
            continue
        pool.append(((kind, -shared, GRADES.get(r.get('grade'), 3), bool(r.get('risk_flags')), n), r))
    pool.sort(key=lambda x: x[0])
    turn, out = Counter(), []
    for key, r in pool:
        out.append(((r['sub_clip_id'] in used, key[0], turn[key[0], r['clip_id']]) + key[1:], r))
        turn[key[0], r['clip_id']] += 1
    out.sort(key=lambda x: x[0])
    listed = [{'sub_clip_id': r['sub_clip_id'], 'kind': RANK_KINDS[key[1]]} for key, r in out]
    spare = [x for x in listed if x['kind'] == 'b-roll'][broll:]
    return [x for x in listed if x not in spare]


def with_steps(beats, sentences):
    """design/91 N17: a scene's steps are its timed sentences, numbered BEAT_03.S2; a sentence belongs to the scene its first word starts in."""
    out = []
    for b in beats:
        own = [s for s in sentences or [] if b['timeline_start_frame'] <= s['start_frame'] < b['timeline_end_frame']]
        out.append({**b, 'steps': [{'step_id': f"{b['beat_id']}.S{n}", 'text': s['text'], 'start_frame': s['start_frame'], 'end_frame': s['end_frame']} for n, s in enumerate(own, 1)]})
    return out


def build(run, production, beats, cards, rows, landmarks, entities, learned_rules, timeline, policy, prompt, narration=None):
    beats = with_steps(beats, (narration or {}).get('sentences'))
    return {'contract': 'vw2-options-package-v1', 'project': {'code': run['code'], 'client': run.get('client'), **production}, 'timeline': timeline, 'policy': policy,
            'narration': narration or {}, 'beats': beats, 'cards': cards, 'sub_clips': rows, 'landmarks': sorted(landmarks), 'entities': entities, 'learned_rules': learned_rules,
            'coverage': coverage(beats, rows, policy), 'prompt': prompt, 'ruled_out': ruled_out(rows), 'ranked': {b['beat_id']: ranked(rows, b) for b in beats}, 'frame_base': FRAME_BASE,   # design/142 R2, R10
            'shapes': {'scenes': SCENES_SHAPE, 'options': {'contract': 'vw2-options-v1', 'options': [{'option_number': 1, 'beat_id': 'BEAT_01',   # design/127: one option per scene
                                                                              'events': [{'sub_clip_id': '', 'source_in_frame': 0, 'source_out_frame': 0, 'hold_last_frame': False, 'crop': 'solver|full|hands_only',
                                                                                          'a2_intervals': [{'in_frame': 0, 'out_frame': 0}], 'marker': {'name': '', 'note': '', 'colour': 'Blue'},
                                                                                          'match': 'direct|b_roll', 'evidence': 'the log fields showing this shot shows the words it sits under',
                                                                                          'short': 'only on a shot cut under its hold: ' + '|'.join(SHORT),   # VW-25 issue 3b
                                                                                          'note': {'kind': 'reuse|check_by_eye|poor_quality|join|other', 'question': 'what the operator should look at'},
                                                                                          'alternatives': [{'sub_clip_id': '', 'source_in_frame': 0, 'source_out_frame': 0, 'crop': 'solver|full|hands_only', 'match': 'direct|b_roll',
                                                                                                            'evidence': 'another clip for the same words, the same length, used nowhere else'}],
                                                                                          'preferred_because': 'only with alternatives: why this clip beat them',
                                                                                          'carries_over_seen': 'only when its landmark labels name the carried thing another way: why it is the same thing',
                                                                                          'illustrates_word_id': '', 'action_word_id': '',
                                                                                          'marker_reasons': {'illustrates': 'only when no illustrated word can be met: why', 'action': 'only when no action word can be met: why'}},
                                                                                         {'blank': True, 'timeline_frames': 75, 'intent': 'what the AI video or animation must show',
                                                                                          'considered': [{'sub_clip_id': '', 'why': 'wrong action|wrong object|already used|claim or number|too short|unusable crop|contradicts the words|other',
                                                                                                          'words': 'only for other'}],
                                                                                          'none_fit': 'instead of considered, when no eligible piece fits these sentences at all'}],
                                                                              'reasoning': 'why these sub-clips, which log fields drove it', 'log_fields_cited': ['SUB_x.primary_fit_for_beats'],
                                                                              'best_unchosen': {'sub_clip_id': '', 'rule': 'the rule that excluded it'},
                                                                              'steps': [{'step_id': 'BEAT_01.S1', 'event': 1, 'why': 'the logged action, process_stage or outcome_state that shows this step',
                                                                                         'claim': False}],   # design/91 N17: every step of the scene once
                                                                              'carries_over': ['what the step before left, which must still be visible'],   # design/91 N14
                                                                              'moves_place': 'only when the narration moves to another place mid-process'}],
                                   'qc_self': {f'Q{i}': {'pass': True, 'evidence': ''} for i in range(1, 9)}}}}
