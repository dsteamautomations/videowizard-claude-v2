"""Scene beats and sentence-end pauses on the existing narration (design/19 A1–A7). Pure arithmetic on the ElevenLabs word timing:
no AI call, nothing re-recorded. The recording is cut only in the silence after a sentence-ending word, on whole frames; silence is
inserted there. A pause states the total silence wanted; the recording's own gap counts toward it, so a voiceover that already
breathes gets nothing extra."""
import re
from fractions import Fraction
from math import ceil

SENTENCE_END = re.compile(r'[.!?…]["\'”’)\]]*$')
MAX_PAUSE_S = 4.0


def frame(seconds, fps):
    return int(round(Fraction(str(seconds)) * Fraction(str(fps))))


def is_sentence_end(word):
    return bool(SENTENCE_END.search(word['text']))


def sentence_ranges(words):
    """[(first_index, last_index)] in order; the last word always closes a sentence."""
    out, start = [], 0
    for i, w in enumerate(words):
        if is_sentence_end(w) or i == len(words) - 1:
            out.append((start, i))
            start = i + 1
    return out


def validate_pauses(words, pauses):
    index = {w['id']: i for i, w in enumerate(words)}
    seen = set()
    for p in pauses or []:
        wid = p.get('after_word_id')
        if wid not in index:
            raise ValueError(f'Pause after unknown word {wid!r}.')
        if wid in seen:
            raise ValueError(f'Two pauses after word {wid}.')
        seen.add(wid)
        i = index[wid]
        if not (is_sentence_end(words[i]) or i == len(words) - 1):
            raise ValueError(f"A pause goes only after a sentence ends; word {wid} ({words[i]['text']!r}) does not end a sentence.")
        s = p.get('seconds')
        if not isinstance(s, (int, float)) or not 0 < s <= MAX_PAUSE_S:
            raise ValueError(f'Pause after {wid}: seconds must be above 0 and at most {MAX_PAUSE_S}.')
        if not str(p.get('reason') or '').strip():
            raise ValueError(f'Pause after {wid} needs a reason.')


def plan(words, audio_duration_s, fps, pauses=()):
    """The timeline narration: cut points, pieces and the source→timeline mapping. All in frames at the timeline fps."""
    validate_pauses(words, pauses)
    fps = Fraction(str(fps))
    index = {w['id']: i for i, w in enumerate(words)}
    end_frame = frame(audio_duration_s, fps)
    cuts = []
    for p in sorted(pauses or [], key=lambda p: index[p['after_word_id']]):
        i = index[p['after_word_id']]
        w = words[i]
        nxt = words[i + 1]['start_s'] if i + 1 < len(words) else float(audio_duration_s)
        gap = max(0.0, nxt - w['end_s'])
        if i + 1 == len(words):
            cut = end_frame
        else:
            cut = frame(w['end_s'] + gap / 2, fps)
            if cut < w['end_s'] * fps and ceil(Fraction(str(w['end_s'])) * fps) <= Fraction(str(nxt)) * fps:
                cut = ceil(Fraction(str(w['end_s'])) * fps)   # never cut into the sentence's last word
        inserted = max(0, frame(max(0.0, p['seconds'] - gap), fps))
        cuts.append({'after_word_id': p['after_word_id'], 'source_cut_frame': cut, 'natural_gap_s': round(gap, 3), 'requested_s': p['seconds'],
                     'inserted_frames': inserted, 'reason': p['reason']})

    def to_timeline(source_frame):
        return source_frame + sum(c['inserted_frames'] for c in cuts if c['source_cut_frame'] <= source_frame)

    bounds = [0] + [c['source_cut_frame'] for c in cuts if c['source_cut_frame'] < end_frame] + [end_frame]
    pieces = [{'source_start_frame': a, 'source_end_frame': b, 'timeline_start_frame': to_timeline(a) if a else 0}
              for a, b in zip(bounds, bounds[1:]) if b > a]
    total = to_timeline(end_frame)
    return {'fps': str(fps), 'cuts': cuts, 'pieces': pieces, 'total_frames': total, 'source_frames': end_frame,
            'inserted_frames': sum(c['inserted_frames'] for c in cuts)}, to_timeline


def word_rows(words, fps, to_timeline):
    return [{'id': w['id'], 'text': w['text'], 'start_frame': to_timeline(frame(w['start_s'], fps)), 'end_frame': to_timeline(frame(w['end_s'], fps)),
             'sentence_end': is_sentence_end(w)} for w in words]


def sentences(words, fps, to_timeline):
    out = []
    for a, b in sentence_ranges(words):
        out.append({'first_word_id': words[a]['id'], 'last_word_id': words[b]['id'], 'text': ' '.join(w['text'] for w in words[a:b + 1]),
                    'source_start_s': words[a]['start_s'], 'source_end_s': words[b]['end_s'],
                    'start_frame': to_timeline(frame(words[a]['start_s'], fps)), 'end_frame': to_timeline(frame(words[b]['end_s'], fps))})
    return out


def silences(words, fps, to_timeline, total_frames, min_s=1.2):
    """Timeline intervals of at least min_s with no narration (natural gaps and inserted pauses)."""
    fps = Fraction(str(fps))
    marks = [(0, 0)] + [(to_timeline(frame(w['start_s'], fps)), to_timeline(frame(w['end_s'], fps))) for w in words] + [(total_frames, total_frames)]
    out = []
    for (_, end), (start, _) in zip(marks, marks[1:]):
        if Fraction(start - end) / fps >= Fraction(str(min_s)):
            out.append({'start_frame': end, 'end_frame': start})
    return out


def validate_scenes(words, scenes, process_stages=()):
    if not isinstance(scenes, list) or not scenes:
        raise ValueError('Give at least one scene.')
    index = {w['id']: i for i, w in enumerate(words)}
    starts = {a for a, _ in sentence_ranges(words)}
    previous = -1
    allowed = set(process_stages or [])
    for n, s in enumerate(scenes, 1):
        wid = s.get('first_word_id')
        if wid not in index:
            raise ValueError(f'Scene {n} starts at unknown word {wid!r}.')
        i = index[wid]
        if n == 1 and i != 0:
            raise ValueError(f"Scene 1 must start at the first word ({words[0]['id']}).")
        if i <= previous:
            raise ValueError(f'Scene {n} must start after scene {n - 1}.')
        if i not in starts:
            raise ValueError(f"Scene {n} must start at the beginning of a sentence; {wid} ({words[i]['text']!r}) is inside one.")
        if not str(s.get('title') or '').strip():
            raise ValueError(f'Scene {n} needs a title.')
        for st in s.get('process_stages') or []:
            if allowed and st not in allowed:
                raise ValueError(f'Scene {n}: process stage {st!r} is not in the brief ({", ".join(sorted(allowed))}).')
        previous = i


def beats(words, scenes, narration_plan, to_timeline, fps, ids=None):
    """Scene i runs from its boundary to the next one. A boundary that carries a pause sits after the silence, so the silence belongs
    to the scene that just ended (the picture runs on while the narration rests)."""
    fps = Fraction(str(fps))
    index = {w['id']: i for i, w in enumerate(words)}
    cut_before = {}   # word index → cut that sits right before it
    for c in narration_plan['cuts']:
        i = index[c['after_word_id']]
        if i + 1 < len(words):
            cut_before[i + 1] = c
    firsts = [index[s['first_word_id']] for s in scenes]
    out = []
    for n, (s, i) in enumerate(zip(scenes, firsts)):
        last = (firsts[n + 1] - 1) if n + 1 < len(firsts) else len(words) - 1
        if n == 0:
            start = 0
        elif i in cut_before:
            start = to_timeline(cut_before[i]['source_cut_frame'])
        else:
            start = to_timeline(frame(words[i]['start_s'], fps))
        nxt = firsts[n + 1] if n + 1 < len(firsts) else None
        if nxt is None:
            end = narration_plan['total_frames']
        elif nxt in cut_before:
            end = to_timeline(cut_before[nxt]['source_cut_frame'])
        else:
            end = to_timeline(frame(words[nxt]['start_s'], fps))
        if end <= start:
            raise ValueError(f"Scene {n + 1} has no length on the timeline.")
        bid = (ids[n] if ids else f'BEAT_{n + 1:02d}')
        out.append({'beat_id': bid, 'title': s.get('title') or '', 'process_stages': list(s.get('process_stages') or []), 'passage_id': s.get('passage_id'),
                    'first_word_id': words[i]['id'], 'last_word_id': words[last]['id'], 'text': ' '.join(w['text'] for w in words[i:last + 1]),
                    'timeline_start_frame': start, 'timeline_end_frame': end, 'target_beat_frames': end - start,
                    'narration_first_word_s': words[i]['start_s'], 'narration_last_word_s': words[last]['end_s'],
                    'window_start_s': float(Fraction(start) / fps), 'window_end_s': float(Fraction(end) / fps),
                    'pauses': [c for c in narration_plan['cuts'] if i <= index[c['after_word_id']] <= last]})
    return out


def paragraph_scenes(script_beats, words):
    """The default when no scene split is approved: one scene per script paragraph, as before."""
    out = []
    for b in script_beats:
        own = [w for w in words if w['passage_id'] == b['passage_id']]
        if not own:
            raise ValueError(f"narration timing has no words for {b['beat_id']}")
        out.append({'first_word_id': own[0]['id'], 'title': b['beat_id'], 'process_stages': [], 'passage_id': b['passage_id']})
    return out
