"""Apply only model-requested silence at mapped narration passage endings."""
from copy import deepcopy
import math


def apply_pauses(plan, context, segments, error):
    pauses = plan.get('narration_pauses')
    if not isinstance(pauses, list):
        raise error('v2 narration_pauses must be an explicit array.')
    fps = plan['fps']
    words = deepcopy(context.get('mapped_words'))
    passage_ids = context.get('passage_ids', [])
    if not isinstance(words, list) or not words:
        raise error('v2 needs mapped words for narration pause boundaries.')
    by_passage = {p: [] for p in passage_ids}
    previous_source = previous_timeline = -1
    for word in words:
        if not isinstance(word, dict) or word.get('passage_id') not in by_passage:
            raise error('Mapped word passage is missing or unknown.')
        values = [word.get(k) for k in ('source_start_s', 'source_end_s', 'timeline_start_s', 'timeline_end_s')]
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
            raise error('Mapped word times must be finite nonnegative seconds.')
        a, b, lo, hi = values
        if b <= a or hi <= lo or abs((b-a)-(hi-lo)) > 1e-7 or a < previous_source-1e-7 or lo < previous_timeline-1e-7:
            raise error('Mapped words overlap, change speed or are out of order.')
        if not any(a >= s['source_start_s']-1e-7 and b <= s['source_end_s']+1e-7
                   and abs(lo-(s['timeline_start_s']+a-s['source_start_s'])) < 1e-7 for s in segments):
            raise error('Mapped word does not match the canonical audio mapping.')
        previous_source, previous_timeline = b, hi
        by_passage[word['passage_id']].append(word)
    if any(not value for value in by_passage.values()):
        raise error('Every passage needs mapped words before pauses can be applied.')
    bounds = [(by_passage[p][0]['timeline_start_s'], by_passage[p][-1]['timeline_end_s']) for p in passage_ids]
    if any(bounds[i][0] < bounds[i-1][1]-1e-7 for i in range(1, len(bounds))):
        raise error('Passage word ranges are out of order or cross another passage.')
    added, previous_index, previous_boundary, explicit = 0, -1, -1, []
    for pause in pauses:
        if not isinstance(pause, dict) or set(pause) != {'after_passage_id', 'additional_frames', 'reason'}:
            raise error('Each pause needs after_passage_id, additional_frames and reason only.')
        p, count = pause['after_passage_id'], pause['additional_frames']
        if p not in by_passage or type(count) is not int or count <= 0:
            raise error('Pause needs a known passage and positive integer additional_frames.')
        if not isinstance(pause['reason'], str) or not pause['reason'].strip():
            raise error('Pause reason must be nonempty.')
        index = passage_ids.index(p)
        boundary = by_passage[p][-1]['timeline_end_s']
        if index <= previous_index or boundary <= previous_boundary:
            raise error('Pauses must be unique and in passage order.')
        if any(w['timeline_start_s'] < boundary-1e-7 and w['timeline_end_s'] > boundary+1e-7 for w in words):
            raise error('Pause boundary crosses another word.')
        explicit.append({**deepcopy(pause), 'original_timeline_boundary_s': boundary,
                         'source_boundary_s': by_passage[p][-1]['source_end_s'],
                         'timeline_start_s': boundary+added/fps,
                         'timeline_end_s': boundary+(added+count)/fps})
        added += count
        previous_index, previous_boundary = index, boundary
    if plan['duration_frames'] != context['duration_frames'] + added:
        raise error('Timeline duration must equal the original duration plus added pause frames.')
    shifted = []
    for segment_index, s in enumerate(segments):
        original_id = s.get('segment_id', s.get('id'))
        if original_id is None:
            word_ids = {w['segment_id'] for w in words if w.get('segment_id') is not None
                        and w['source_start_s'] >= s['source_start_s']-1e-7
                        and w['source_end_s'] <= s['source_end_s']+1e-7}
            if len(word_ids) > 1:
                raise error('Canonical audio segment has inconsistent mapped word segment IDs.')
            original_id = next(iter(word_ids), None)
        lo, hi = s['timeline_start_s'], s['timeline_end_s']
        cuts = [lo] + [p['original_timeline_boundary_s'] for p in explicit if lo+1e-7 < p['original_timeline_boundary_s'] < hi-1e-7] + [hi]
        for a, b in zip(cuts, cuts[1:]):
            offset = sum(p['additional_frames'] for p in explicit if p['original_timeline_boundary_s'] <= a+1e-7)/fps
            shifted.append({**deepcopy(s), 'id': f'direct-audio-{len(shifted)+1:04d}',
                            'segment_id': f'direct-audio-{len(shifted)+1:04d}',
                            'original_segment_id': original_id, 'original_segment_index': segment_index,
                            'source_start_s': s['source_start_s']+a-lo,
                            'source_end_s': s['source_start_s']+b-lo,
                            'timeline_start_s': a+offset, 'timeline_end_s': b+offset})
    for word in words:
        offset = sum(p['additional_frames'] for p in explicit if p['original_timeline_boundary_s'] <= word['timeline_start_s']+1e-7)/fps
        word['timeline_start_s'] += offset
        word['timeline_end_s'] += offset
        matches = [s for s in shifted if word['source_start_s'] >= s['source_start_s']-1e-7
                   and word['source_end_s'] <= s['source_end_s']+1e-7
                   and abs(word['timeline_start_s']-(s['timeline_start_s']+word['source_start_s']-s['source_start_s'])) < 1e-7]
        if len(matches) != 1:
            raise error('Shifted word must bind to exactly one narration segment.')
        original_word_id = word.get('segment_id')
        if original_word_id is not None and original_word_id != matches[0]['original_segment_id']:
            raise error('Mapped word segment identity conflicts with its canonical audio segment.')
        word['original_segment_id'] = original_word_id
        word['segment_id'] = matches[0]['segment_id']
    speech = [(min(w['timeline_start_s'] for w in words if w['passage_id'] == p),
               max(w['timeline_end_s'] for w in words if w['passage_id'] == p)) for p in passage_ids]
    starts = [0] + [a for a, b in speech[1:]]
    ends = starts[1:] + [plan['duration_frames']/fps]
    windows = [{'passage_id': p, 'timeline_start_s': a, 'timeline_end_s': b,
                'duration_s': round(b-a, 9), 'speech_start_s': spoken[0], 'speech_end_s': spoken[1]}
               for p, a, b, spoken in zip(passage_ids, starts, ends, speech)]
    return shifted, {'mapped_words': words, 'passage_windows': windows, 'applied_narration_pauses': explicit,
                     'original_duration_frames': context['duration_frames']}
